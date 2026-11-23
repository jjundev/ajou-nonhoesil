# Run every testbench with Questa. Exit code 1 if any of them fails.
# Questa's vopt cannot read files under a non-ASCII path, so the sources are
# copied to an ASCII folder under TEMP and simulated there.
$bin = 'C:\intelFPGA_lite\22.1std\questa_fse\win64'
$build = Join-Path $env:TEMP 'doorlock_sim'
if (Test-Path $build) { Remove-Item -Recurse -Force $build }
New-Item -ItemType Directory $build | Out-Null
Copy-Item -Recurse (Join-Path $PSScriptRoot 'rtl'), (Join-Path $PSScriptRoot 'tb') $build
Push-Location $build
$failed = 0
try {
    & "$bin\vlib.exe" work | Out-Null
    $src = @(Get-ChildItem rtl\*.v) + @(Get-ChildItem tb\*.v) |
        ForEach-Object { "$($_.Directory.Name)/$($_.Name)" }
    & "$bin\vlog.exe" -quiet -vlog01compat -lint +incdir+rtl -work work @src
    if ($LASTEXITCODE -ne 0) { 'COMPILE FAILED'; exit 1 }
    foreach ($tb in Get-ChildItem tb\*.v) {
        $name = $tb.BaseName
        $out = & "$bin\vsim.exe" -c -lib work $name -do 'run 2 sec; quit -f' 2>&1 | ForEach-Object { "$_" }
        $out | Where-Object { $_ -match '^# (RESULT|FAIL|\*\* (Error|Warning|Fatal))' }
        if (-not ($out -match "RESULT PASS $name")) { $failed++; "NOT PASSED: $name" }
    }
} finally { Pop-Location }
if ($failed) { exit 1 }
'ALL PASS'
