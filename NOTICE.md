# Notice

This repository is an unofficial fork of [CorgiTaco-MC/Oh-The-Trees-Youll-Grow](https://github.com/CorgiTaco-MC/Oh-The-Trees-Youll-Grow).

The Minecraft 26.2 Fabric fix starts from upstream commit [`528ce615d4c3362748dbe9a929c75e6782543515`](https://github.com/CorgiTaco-MC/Oh-The-Trees-Youll-Grow/commit/528ce615d4c3362748dbe9a929c75e6782543515). The modified source is published on branch `fix/26.2-saved-chunk-ticks` and at tag `mc26.2-fabric-11.0.2-chunkfix.1`.

Changes made by this fork:

- Read `scheduled_random_ticks` from the nested `ohthetreesyoullgrow` chunk data written by the serializer.
- Restore decoded ticks to the wrapped `LevelChunk` when Minecraft returns an `ImposterProtoChunk`.
- Version the Fabric-only test build as `11.0.2-chunkfix.1`.
- Declare the tested Minecraft 26.2, Fabric Loader, Fabric API, and Java requirements.

The original project and this modified source are distributed under the Mozilla Public License 2.0. The complete license remains in [LICENSE](LICENSE) and is packaged in the release jar.

Project names and links identify the upstream work. They do not imply sponsorship, endorsement, or an official upstream release. This fork contains no Oh The Biomes We've Gone source code, assets, or binaries.
