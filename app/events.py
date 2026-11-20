"""Outbox transaccional, confirmaciones del broker e idempotencia del consumidor."""
import argparse
import json
import logging
import time

import pika
from sqlalchemy import select

from app.config import Settings
from app.db import Outbox, database, process_event

log = logging.getLogger("preflop.events")
QUEUE = "ep3-preflop.analyses"
DEAD = "ep3-preflop.failed"


def channel_for(settings):
    params = pika.URLParameters(settings.rabbit_url)
    params.heartbeat = 30
    params.blocked_connection_timeout = 10
    connection = pika.BlockingConnection(params)
    channel = connection.channel()
    channel.queue_declare(queue=DEAD, durable=True)
    channel.queue_declare(queue=QUEUE, durable=True, arguments={"x-dead-letter-exchange": "", "x-dead-letter-routing-key": DEAD})
    channel.basic_qos(prefetch_count=1)
    channel.confirm_delivery()
    return connection, channel


def publish_pending(sessions, channel):
    with sessions.begin() as session:
        items = session.scalars(select(Outbox).where(Outbox.published.is_(False)).order_by(Outbox.id).limit(50).with_for_update(skip_locked=True)).all()
        for item in items:
            channel.basic_publish(exchange="", routing_key=QUEUE, mandatory=True,
                body=json.dumps({"event_id": item.id, "analysis_id": item.analysis_id}),
                properties=pika.BasicProperties(delivery_mode=2, content_type="application/json", message_id=item.id))
            item.published = True
        return len(items)


def callback(sessions, channel, method, properties, body):
    event_id = None
    try:
        payload = json.loads(body)
        event_id = payload["event_id"]
        with sessions.begin() as session:
            changed = process_event(session, event_id)
        channel.basic_ack(method.delivery_tag)
        log.info(json.dumps({"event_id": event_id, "processed": changed}))
    except Exception as exc:
        retry = False
        if event_id:
            with sessions.begin() as session:
                item = session.get(Outbox, event_id)
                if item:
                    item.attempts += 1
                    item.last_error = type(exc).__name__
                    retry = item.attempts < 3
        channel.basic_nack(method.delivery_tag, requeue=retry)
        log.warning(json.dumps({"event_id": event_id, "retry": retry, "error": type(exc).__name__}))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("role", choices=["publisher", "worker"])
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    settings = Settings.from_env()
    _, sessions = database(settings.database_url)
    while True:
        connection = None
        try:
            connection, channel = channel_for(settings)
            if args.role == "publisher":
                while True:
                    publish_pending(sessions, channel)
                    connection.process_data_events(time_limit=1)
                    time.sleep(0.2)
            else:
                channel.basic_consume(queue=QUEUE, on_message_callback=lambda ch, m, p, b: callback(sessions, ch, m, p, b))
                channel.start_consuming()
        except KeyboardInterrupt:
            break
        except Exception as exc:
            log.warning(json.dumps({"role": args.role, "reconnecting": True, "error": type(exc).__name__}))
            time.sleep(3)
        finally:
            if connection and connection.is_open:
                connection.close()


if __name__ == "__main__":
    main()

