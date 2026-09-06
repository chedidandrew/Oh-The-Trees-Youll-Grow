# Fabric 26.2 saved chunk fix

## Scope

| Item | Value |
|---|---|
| Upstream repository | [CorgiTaco-MC/Oh-The-Trees-Youll-Grow](https://github.com/CorgiTaco-MC/Oh-The-Trees-Youll-Grow) |
| Upstream branch | `26.2` |
| Base commit | [`528ce615d4c3362748dbe9a929c75e6782543515`](https://github.com/CorgiTaco-MC/Oh-The-Trees-Youll-Grow/commit/528ce615d4c3362748dbe9a929c75e6782543515) |
| Fixed version | `11.0.2-chunkfix.1` |
| Target | Minecraft 26.2, Fabric Loader 0.19.3 or newer, Fabric API 0.152.2 or newer, Java 25 or newer |
| Release tag | `mc26.2-fabric-11.0.2-chunkfix.1` |
| Expected jar SHA-256 | `5b80134bba4140b02d93eb1bb64b746e6e9011afbdde65e3c39985775247d82d` |

This is an unofficial community build, not an official CorgiTaco release.

## Defect

The upstream chunk deserializer obtains the nested `ohthetreesyoullgrow` compound and confirms that it contains `scheduled_random_ticks`, but then attempts to read the list from the outer structure-data compound. The missing outer value raises `NoSuchElementException` when affected saved chunks load.

Minecraft can return an `ImposterProtoChunk` around an already-full saved `LevelChunk`. Restoring ticks to that wrapper loses them when Minecraft unwraps the existing full chunk.

## Fix

The reader now:

1. Reads `scheduled_random_ticks` from `corgiLibTag`, matching the writer.
2. Detects `ImposterProtoChunk` and targets its wrapped `LevelChunk`.
3. Keeps the original path for ordinary `ProtoChunk` instances.

The build metadata assigns a distinct version, requires the tested Fabric 26.2 runtime, and limits this branch to the Common and Fabric modules.

## Reproduce the jar

Use Ubuntu 24.04, Zulu JDK 25, and the repository's Gradle wrapper:

```bash
chmod +x gradlew
./gradlew --no-daemon :common:publishToMavenLocal :fabric:publishToMavenLocal :fabric:build --stacktrace
sha256sum fabric/build/libs/ohthetreesyoullgrow-fabric-26.2-11.0.2-chunkfix.1.jar
```

The build must produce:

```text
5b80134bba4140b02d93eb1bb64b746e6e9011afbdde65e3c39985775247d82d  ohthetreesyoullgrow-fabric-26.2-11.0.2-chunkfix.1.jar
```

The GitHub workflow also CRC-reads all 94 jar entries, rejects duplicate entries, validates Fabric metadata, checks Java 25 bytecode, confirms the MPL license is packaged, and verifies the compiled call to `ImposterProtoChunk.getWrapped()`.

## Validation record

The same source edits produced the expected jar in GitHub Actions run [34016565305](https://github.com/chedidandrew/No_Sky_Islands/actions/runs/34016565305).

That integration test:

- Built Common and Fabric from this exact upstream base.
- Built the dependent biome mod against exactly `11.0.2-chunkfix.1`.
- Booted a Minecraft 26.2 Fabric server twice on the same world.
- Injected the exact nested saved-tick NBT shape into a full saved chunk between boots.
- Reopened the world without the original exception, chunk-load errors, registry errors, or mixin failures.
- Verified the compiled unwrapping call and the final jar archive.

Andrew then confirmed the paired mods worked in the Minecraft 26.2 Fabric client on 2026-09-06. The public release contains only this MPL-licensed library.

## Installation

Remove any other Oh The Trees You'll Grow jar before installing this release. Two jars with the same mod ID must not be installed together. Existing worlds and chunks do not need to be deleted or regenerated for this fix.
