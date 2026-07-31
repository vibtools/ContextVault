# Verify a ContextVault Release

The official Windows release includes:

```text
ContextVault-Windows-x64.zip
ContextVault-Windows-x64.zip.sha256
```

The checksum confirms that the downloaded ZIP matches the file produced by the release workflow.

## PowerShell verification

Place both files in the same folder and run:

```powershell
$zip = ".\ContextVault-Windows-x64.zip"
$checksumFile = ".\ContextVault-Windows-x64.zip.sha256"

if (-not (Test-Path -LiteralPath $zip)) {
    throw "Release ZIP not found: $zip"
}

if (-not (Test-Path -LiteralPath $checksumFile)) {
    throw "Checksum file not found: $checksumFile"
}

$expected = ((Get-Content -LiteralPath $checksumFile -Raw).Trim() -split "\s+")[0].ToLowerInvariant()
$actual = (Get-FileHash -LiteralPath $zip -Algorithm SHA256).Hash.ToLowerInvariant()

if ($actual -ne $expected) {
    throw "Checksum verification failed. Expected $expected but received $actual."
}

"Checksum verified: $actual"
```

Expected result:

```text
Checksum verified: <64-character SHA-256 value>
```

## Manual comparison

You may also run:

```powershell
Get-FileHash ".\ContextVault-Windows-x64.zip" -Algorithm SHA256
Get-Content ".\ContextVault-Windows-x64.zip.sha256"
```

Compare the two 64-character values without regard to letter case.

## When verification fails

Do not run the ZIP.

1. Delete both downloaded files.
2. Download them again from the official repository release.
3. Verify the tag and filenames.
4. Run the checksum check again.

A mismatch can result from an incomplete download, a modified file, a wrong checksum file, a third-party mirror, or local storage corruption.

## Verify the extracted package

After extraction, confirm that the top-level distribution includes:

```text
ContextVault.exe
README.txt
LICENSE
data\
exports\
logs\
runtime\
```

Keep the complete runtime beside the executable.

## Source authenticity

Use only release assets attached to:

```text
https://github.com/vibtools/ContextVault/releases
```

Do not trust an executable sent through an unrelated file-sharing service unless you independently verify its source and checksum.
