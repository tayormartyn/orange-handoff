# OQ-10 OCR TRIAL — Windows-native Windows.Media.Ocr, zero new dependencies (D-043 approval).
# READ-ONLY over stored media; prints recognized text per image for the accuracy gate.
param([string[]]$Paths)
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
    $task.Wait()
    $task.Result
}

$engine = [Windows.Media.Ocr.OcrEngine]::TryCreateFromUserProfileLanguages()
if (-not $engine) { $engine = [Windows.Media.Ocr.OcrEngine]::TryCreateFromLanguage([Windows.Globalization.Language]::new("en-US")) }
if (-not $engine) { Write-Output "OCR_ENGINE_UNAVAILABLE"; exit 1 }
Write-Output ("ENGINE_LANG=" + $engine.RecognizerLanguage.LanguageTag)

foreach ($p in $Paths) {
    Write-Output ("=== FILE " + (Split-Path $p -Leaf))
    $file = Await ([Windows.Storage.StorageFile]::GetFileFromPathAsync($p)) ([Windows.Storage.StorageFile])
    $stream = Await ($file.OpenReadAsync()) ([Windows.Storage.Streams.IRandomAccessStreamWithContentType])
    $decoder = Await ([Windows.Graphics.Imaging.BitmapDecoder]::CreateAsync($stream)) ([Windows.Graphics.Imaging.BitmapDecoder])
    $bitmap = Await ($decoder.GetSoftwareBitmapAsync()) ([Windows.Graphics.Imaging.SoftwareBitmap])
    $result = Await ($engine.RecognizeAsync($bitmap)) ([Windows.Media.Ocr.OcrResult])
    foreach ($line in $result.Lines) { Write-Output ("LINE: " + $line.Text) }
    $stream.Dispose()
}
