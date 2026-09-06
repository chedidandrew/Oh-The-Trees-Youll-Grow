# Unofficial Fabric 26.2 saved chunk fix

This prerelease provides Oh The Trees You'll Grow `11.0.2-chunkfix.1` for Minecraft 26.2 Fabric. It is an unofficial community build and is not endorsed by the upstream project.

## What it fixes

- Reads saved scheduled random ticks from the correct nested `ohthetreesyoullgrow` NBT compound.
- Restores those ticks to the wrapped `LevelChunk` when Minecraft returns an `ImposterProtoChunk`.
- Prevents the observed `NoSuchElementException`, repeated chunk-load failures, and loss of restored ticks.

## Requirements

- Minecraft `26.2`
- Fabric Loader `0.19.3` or newer
- Fabric API `0.152.2` or newer
- Java `25` or newer

Remove any other Oh The Trees You'll Grow jar before installing this one. Existing chunks do not need to be deleted or regenerated.

## Verification

The release workflow builds directly from the tagged source and accepts the jar only when its SHA-256 is:

```text
5b80134bba4140b02d93eb1bb64b746e6e9011afbdde65e3c39985775247d82d
```

The archive is also checked for all 94 readable, unique entries, exact Fabric metadata, Java 25 bytecode, the fixed compiled method call, and the packaged MPL 2.0 license. The two-boot saved-world regression passed, and Andrew confirmed the paired mods work in a Minecraft 26.2 Fabric client.

Exact source and technical details: [PORTING.md](https://github.com/chedidandrew/Oh-The-Trees-Youll-Grow/blob/mc26.2-fabric-11.0.2-chunkfix.1/PORTING.md)

This release contains no Oh The Biomes We've Gone source code, assets, or binaries.
