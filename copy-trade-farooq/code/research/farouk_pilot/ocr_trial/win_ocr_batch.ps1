# OQ-10 FULL PASS — batch Windows.Media.Ocr over a path-list file. READ-ONLY.
# Output: one line "=== FILE <name>" per image then "LINE: <text>" rows; "!! ERROR <name> <type>" on failure.
param([string]$PathList)
Add-Type -AssemblyName System.Runtime.WindowsRuntime
$null = [Windows.Media.Ocr.OcrEngine, Windows.Foundation, ContentType = WindowsRuntime]
$null = [Windows.Graphics.Imaging.BitmapDecoder, Windows.Graphics.Imaging, ContentType = WindowsRuntime]
$null = [Windows.Storage.StorageFile, Windows.Storage, ContentType = WindowsRuntime]
$awaitMethod = [System.WindowsRuntimeSystemExtensions].GetMethods() |
    Where-Object { $_.Name -eq 'AsTask' -and $_.GetParameters().Count -eq 1 -and
                   $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1' } |
    Select-Object -First 1
function Await($op, [Type]$resultType) {
    $task = $awaitMethod.MakeGenericMethod($resultType).Invoke($null, @($op))
    $task.Wait(); $task.Result
}
$engine = [Windows.Media.Ocr.OcrEngine]::TryCreateFromUserProfileLanguages()
if (-not $engine) { Write-Output "OCR_ENGINE_UNAVAILABLE"; exit 1 }
foreach ($p in (Get-Content $PathList)) {
    if (-not $p.Trim()) { continue }
    try {
        $file = Await ([Windows.Storage.StorageFile]::GetFileFromPathAsync($p)) ([Windows.Storage.StorageFile])
        $stream = Await ($file.OpenReadAsync()) ([Windows.Storage.Streams.IRandomAccessStreamWithContentType])
        $decoder = Await ([Windows.Graphics.Imaging.BitmapDecoder]::CreateAsync($stream)) ([Windows.Graphics.Imaging.BitmapDecoder])
        $bitmap = Await ($decoder.GetSoftwareBitmapAsync()) ([Windows.Graphics.Imaging.SoftwareBitmap])
        $result = Await ($engine.RecognizeAsync($bitmap)) ([Windows.Media.Ocr.OcrResult])
        Write-Output ("=== FILE " + (Split-Path $p -Leaf))
        foreach ($line in $result.Lines) { Write-Output ("LINE: " + $line.Text) }
        $stream.Dispose()
    } catch {
        Write-Output ("!! ERROR " + (Split-Path $p -Leaf) + " " + $_.Exception.GetType().Name)
    }
}
