<# Demostración REST con curl.exe real. No requiere contraseña ni muestra la cookie. #>
param([uri]$BaseUrl='https://54.162.150.183')
$ErrorActionPreference='Stop'
if ($BaseUrl.Scheme -ne 'https') {throw 'La demostración remota requiere HTTPS.'}
$demoBase=$BaseUrl.AbsoluteUri.TrimEnd('/')
$demoId=[guid]::NewGuid().ToString('N')
$demoCookie=Join-Path ([IO.Path]::GetTempPath()) ('ep3-demo-'+$demoId+'.cookies')
$demoBody=Join-Path ([IO.Path]::GetTempPath()) ('ep3-demo-'+$demoId+'.json')
function Invoke-DemoCurl([string[]]$CurlArguments) {
    $response=& curl.exe --silent --show-error --fail --connect-timeout 10 --max-time 30 @CurlArguments
    if ($LASTEXITCODE -ne 0) {throw ('curl devolvió código '+$LASTEXITCODE+'. Revisar laboratorio, TLS y endpoint.')}
    $response | ConvertFrom-Json | ConvertTo-Json -Depth 15
}
try {
    Write-Host "1. POST /v1/demo/session: sesión invitada, sin contraseña" -ForegroundColor Cyan
    Invoke-DemoCurl -CurlArguments @('--request','POST','--cookie-jar',$demoCookie,"$demoBase/v1/demo/session")
    $payload=@{
        scenario='open_BTN';cards=@('As','Kh');actions=@(
            @{position='UTG';action='fold'},
            @{position='HJ';action='fold'},
            @{position='CO';action='fold'}
        )
    } | ConvertTo-Json -Depth 5
    [IO.File]::WriteAllText($demoBody,$payload,[Text.UTF8Encoding]::new($false))
    Write-Host "2. POST /v1/analyses: As Kh, BTN, folds previos" -ForegroundColor Cyan
    Invoke-DemoCurl -CurlArguments @('--cookie',$demoCookie,'--header','Content-Type: application/json','--data-binary',('@'+$demoBody),"$demoBase/v1/analyses")
    Write-Host "3. GET /v1/dashboard: análisis persistido y estadísticas" -ForegroundColor Cyan
    Invoke-DemoCurl -CurlArguments @('--cookie',$demoCookie,"$demoBase/v1/dashboard")
    Write-Host 'Si el evento aún está pendiente, actualizar el dashboard después. La respuesta no espera al worker.' -ForegroundColor Cyan
} finally {
    foreach ($demoFile in @($demoCookie,$demoBody)) {
        if (Test-Path -LiteralPath $demoFile) {Remove-Item -LiteralPath $demoFile -Force}
    }
}
