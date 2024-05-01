## [4.0.0-beta.9](https://github.com/wizarrrr/wizarr/compare/v4.0.0-beta.8...v4.0.0-beta.9) (2024-04-25)


### New Features

* ✨ :sparkles: Emby users can now set max streams ([3b0d4e0](https://github.com/wizarrrr/wizarr/commit/3b0d4e003d2e40a59cbd8c52f3cb4d0b868cecb7))
* 🎉 :sparkles: Scanning in Emby users now attaches connect email as user email ([46d6f22](https://github.com/wizarrrr/wizarr/commit/46d6f226b0cc09713fec0d4e107ed6f4e67e59a9))
* 🎉 Live TV can now be enabled/disabled for Jellyfin/Emby invites ([8723d1c](https://github.com/wizarrrr/wizarr/commit/8723d1ce34cc7159ddef014837d54cd9afb307ff))
* 🎊 :sparkles: Emby and Jellyfin now update username/email on an updated scan ([7c158ca](https://github.com/wizarrrr/wizarr/commit/7c158caaec967e0863ba3f5ced73dca21ef1047e))


### Bug Fixes

* 🐛 :bug: Fixed issue where Emby/Plex would error on creating an invite ([eb54d32](https://github.com/wizarrrr/wizarr/commit/eb54d326e5d6add26fb705cb19448f32e12574c1))
* 🐝 Corrected Live TV for Jellyfin ([1b94a6e](https://github.com/wizarrrr/wizarr/commit/1b94a6eaee7205350a22b53ebf61af2d0e620c61))
* 🩹 Default Live TV checkbox to enabled to reflect Jellyfin/Emby default ([1cba8c3](https://github.com/wizarrrr/wizarr/commit/1cba8c3fea60c8962aea6570e8984b79069ab518))


### Chores

* 🧹 bump db migration script version/date ([a71ada5](https://github.com/wizarrrr/wizarr/commit/a71ada5126c78a6cdb772d46aa355c9a4c2c5546))

## [4.0.0-beta.8](https://github.com/wizarrrr/wizarr/compare/v4.0.0-beta.7...v4.0.0-beta.8) (2024-04-21)


### New Features

* 🚑 added ability to specify concurrent sessions on jellyfin ([#378](https://github.com/wizarrrr/wizarr/issues/378)) ([062bc6b](https://github.com/wizarrrr/wizarr/commit/062bc6b5e0fa791d28973933c7752f54348cb0f8)), closes [#377](https://github.com/wizarrrr/wizarr/issues/377)


### Bug Fixes

* 🩹 :bug: Fixed issue where Jellyseerr could not be selected for Emby servers ([83c381a](https://github.com/wizarrrr/wizarr/commit/83c381a0707fdcbf31f2ee101c5fa405edd9bec6))
* **discord-release-alert:** 🐛 mentions failing in embeded payload ([8e87c41](https://github.com/wizarrrr/wizarr/commit/8e87c414a9d333e0c9dcf0722d794b83658e5d08))

## [4.0.0-beta.7](https://github.com/wizarrrr/wizarr/compare/v4.0.0-beta.6...v4.0.0-beta.7) (2024-04-19)


### New Features

* 🎉 :sparkles: Added Emby Support ([c882992](https://github.com/wizarrrr/wizarr/commit/c882992bda7799b97f98c6c4f6fd0e4d7d4e7db7))


### Bug Fixes

* 🐛 :memo: Fix the form being the wrong namr ([602d5d1](https://github.com/wizarrrr/wizarr/commit/602d5d1b2d41152316efd3d13e0c92f2310959f1))
* 🩹 :art: Resolved scaling of theme selector on help wizard ([ccf75fc](https://github.com/wizarrrr/wizarr/commit/ccf75fc91069a7ffc05d078a75fd3cfcb40c3940))
* 🩹 change delete user call to emby function ([139cf86](https://github.com/wizarrrr/wizarr/commit/139cf86053198efa1c9f800cb414998a416a2852))


### Chores

* 🧽 remove changelog test file ([3191b0a](https://github.com/wizarrrr/wizarr/commit/3191b0a0c59bd4ba89c4684d5e9bf1641c970ebf))


### Documentation

* 📖 :memo: Corrected grammatical issues with Download page on Jellyfin ([0ba2a78](https://github.com/wizarrrr/wizarr/commit/0ba2a78aa93c9f0616f81fb620a1a7ef581f66b8))
* 📚 :memo: Fixed Emby showing in the Jellyfin download page ([4302699](https://github.com/wizarrrr/wizarr/commit/43026990eb3a1254ad08104c75a96d291382c2a6))
* **readme:** 📚 update discord release channel ([7d8afc9](https://github.com/wizarrrr/wizarr/commit/7d8afc9cb6d0d21baaeaa7db5da3cc85b655d286))


### Style Changes

* 💎 minor corrections to discord alert payload ([c03c2cf](https://github.com/wizarrrr/wizarr/commit/c03c2cf2750e1e6c7e70bca46d56ac1fbe9094f2))
* **discord-webhook:** 🎨 role mentions for new channel structure ([2c30e4c](https://github.com/wizarrrr/wizarr/commit/2c30e4c8fa0c32df439f5ca21140381e566aa8ef))

## [4.0.0-beta.6](https://github.com/wizarrrr/wizarr/compare/v4.0.0-beta.5...v4.0.0-beta.6) (2024-04-18)


### Style Changes

* 💎 simplify image tag condition ([8930479](https://github.com/wizarrrr/wizarr/commit/893047977c744d6d3b0d1f7a2103df3e31051c02))
* another correction for the backticks ([428fec7](https://github.com/wizarrrr/wizarr/commit/428fec715190991e321469dd4d2c4be15ee8f622))
* backticks corrected ([eb4259a](https://github.com/wizarrrr/wizarr/commit/eb4259a235d7a319dd340c86223385c53cf81ca4))
* fix backticks reaking payload formatting ([0ebf1c7](https://github.com/wizarrrr/wizarr/commit/0ebf1c7bacf81fef88fba9d9fc63de2d12c7a99f))
* simplify image tag statement check ([96a18ae](https://github.com/wizarrrr/wizarr/commit/96a18ae5754f725380cfee27a4cc85ba119b3369))

## [4.0.0-beta.5](https://github.com/wizarrrr/wizarr/compare/v4.0.0-beta.4...v4.0.0-beta.5) (2024-04-18)


### Build System

* **npm:** add conventionalcommit changelog package ([633868a](https://github.com/wizarrrr/wizarr/commit/633868acbce4f8e5e92c2a9871bbef52dd8a990b))
* **semantic-release:** use conventioncommits preset ([582982f](https://github.com/wizarrrr/wizarr/commit/582982fe714211d095993b2d6310530b7ec1256b))


### Documentation

* **test:** changelog ([a09f31c](https://github.com/wizarrrr/wizarr/commit/a09f31ccdd97ca2738eb9ec0874c6ead420c4c6c))


### Style Changes

* add specifc image tag targeting beta/latest ([71da180](https://github.com/wizarrrr/wizarr/commit/71da180731eec9f79d5ead5b1e8def3cc17a3135))
* fix apostrophe usage ([3be097c](https://github.com/wizarrrr/wizarr/commit/3be097c8de1f50fc9efbe448d47d665618dd2b23))
* removed an extra space ([c96e72e](https://github.com/wizarrrr/wizarr/commit/c96e72e4bedbaaec782e9cedc839d078f470082b))
* update discord webhook message ([d8310a7](https://github.com/wizarrrr/wizarr/commit/d8310a74b06644b59c4907d5ae1b19637cfa196c))


### Code Refactoring

* **test:** changelog ([7e2aacd](https://github.com/wizarrrr/wizarr/commit/7e2aacd315060d88c62cce7e0b479219f7979600))

# [4.0.0-beta.4](https://github.com/wizarrrr/wizarr/compare/v4.0.0-beta.3...v4.0.0-beta.4) (2024-04-18)


### Performance Improvements

* **test:** changelog ([7eacd08](https://github.com/wizarrrr/wizarr/commit/7eacd0820d5c7044378f7247b8b8228911738786))

# [4.0.0-beta.3](https://github.com/wizarrrr/wizarr/compare/v4.0.0-beta.2...v4.0.0-beta.3) (2024-04-18)

# [4.0.0-beta.2](https://github.com/wizarrrr/wizarr/compare/v4.0.0-beta.1...v4.0.0-beta.2) (2024-04-18)


### Bug Fixes

* 🐝 update toast can now be dismissed ([f2585ca](https://github.com/wizarrrr/wizarr/commit/f2585ca30c5e200e7cffb03abe7bf853db2f56a9))

# [4.0.0-beta.1](https://github.com/wizarrrr/wizarr/compare/v3.5.1...v4.0.0-beta.1) (2024-04-11)


### Bug Fixes

* 🐛 refactor server_api.py and software_lifecycle.py for better exception handling ([8cf2b32](https://github.com/wizarrrr/wizarr/commit/8cf2b329a8aeb4a27b783a454a2a58e02230e294))
* 🐝 :bug: Remove trailing slashes on server URL's ([c4cfd77](https://github.com/wizarrrr/wizarr/commit/c4cfd77f5741fb4a25006948e5facc016c76ddc2))
* 🩹 :bug: Fixed copy server URL when override set ([ab5e680](https://github.com/wizarrrr/wizarr/commit/ab5e6804a3f054a48595dc187158ad7a309cb5b3))
* 🩹 :fire: Removed remaining label ([268fda9](https://github.com/wizarrrr/wizarr/commit/268fda9612584591b50926409c0e8b9be57449bc))
* **backend:** user sync error on plex managed/guest users ([#357](https://github.com/wizarrrr/wizarr/issues/357)) ([1467046](https://github.com/wizarrrr/wizarr/commit/146704609d64ba13d1c8a7d80a80fd09e55bfd50))
* **frontend:** 🐛 users without token no longer cause error on scan ([#344](https://github.com/wizarrrr/wizarr/issues/344)) ([05ce4f5](https://github.com/wizarrrr/wizarr/commit/05ce4f5de529993f2cbfc35439f27ddb7933fa73))
* **frontend:** cant remove discord widget id ([#347](https://github.com/wizarrrr/wizarr/issues/347)) ([fefcb06](https://github.com/wizarrrr/wizarr/commit/fefcb065486c9ec7809167744867c66034df208a))
* remove latest info widget ([#353](https://github.com/wizarrrr/wizarr/issues/353)) ([37e21fe](https://github.com/wizarrrr/wizarr/commit/37e21fe98562ec1a9bfec971b251a8a68f429d70))
* **wizarr-backend:** 🚑 added password strength test ([ff83c30](https://github.com/wizarrrr/wizarr/commit/ff83c30302ee44c9113d1419b15358b85b1d8cc9))


### chore

* 🧽 fix versioning file ([66cef97](https://github.com/wizarrrr/wizarr/commit/66cef9765dae0a67f26fa64ef1a73687e3cb5b77))


### Features

* finshed backend password change ([5b1ce2e](https://github.com/wizarrrr/wizarr/commit/5b1ce2e9818cbc8b393623f6642a7b3f4b832e65))
* password reset frontend done, backend started ([d15e0a1](https://github.com/wizarrrr/wizarr/commit/d15e0a1660ef67e5ac294fc375ae989a7d362db8))
* **wizarr-frontend:** 🚀 Add extended labels to buttons ([72c7dc4](https://github.com/wizarrrr/wizarr/commit/72c7dc4f11ad0ff8d2dba3b47071163bc269f4e0))


### Performance Improvements

* 🚀 :sparkles: Changed to use floating vue ([ce0b92f](https://github.com/wizarrrr/wizarr/commit/ce0b92f6359fda7d470033551b4ee68ab3915e40))


### BREAKING CHANGES

* begin 4.x.x versioning

## [3.5.1-beta.7](https://github.com/wizarrrr/wizarr/compare/v3.5.1-beta.6...v3.5.1-beta.7) (2023-11-21)


### Bug Fixes

* 🐛 refactor server_api.py and software_lifecycle.py for better exception handling ([8cf2b32](https://github.com/wizarrrr/wizarr/commit/8cf2b329a8aeb4a27b783a454a2a58e02230e294))

## [3.5.1-beta.6](https://github.com/wizarrrr/wizarr/compare/v3.5.1-beta.5...v3.5.1-beta.6) (2023-11-17)


### Bug Fixes

* 🩹 software lifecycle issue ([15b1edf](https://github.com/wizarrrr/wizarr/commit/15b1edf21ca43086346555f8afa2ac375f303e86))
* 🚑 software lifecycle issue ([ac55841](https://github.com/wizarrrr/wizarr/commit/ac55841b892653d62eda2b3951bf04527b1b4349))
* 🆘 EMERGENCY FIX FOR VERSION 🆘 ([7570ec1](https://github.com/wizarrrr/wizarr/commit/7570ec14d327bfad4000184732f4e329df6e0448))

## [3.5.1-beta.5](https://github.com/wizarrrr/wizarr/compare/v3.5.1-beta.4...v3.5.1-beta.5) (2023-11-17)


### Bug Fixes

* 🔧 release branch identification logic and improve error handling ([e963e0b](https://github.com/wizarrrr/wizarr/commit/e963e0beec90c5d476231e1e149451480342c5d7))

## [3.5.1-beta.4](https://github.com/wizarrrr/wizarr/compare/v3.5.1-beta.3...v3.5.1-beta.4) (2023-11-17)


### Bug Fixes

* 🩹 add formkit stories ([e5cd97b](https://github.com/wizarrrr/wizarr/commit/e5cd97ba0c7c9dcf79ab8c59d888e8e8a326671f))

## [3.5.1-beta.3](https://github.com/Wizarrrr/wizarr/compare/v3.5.1-beta.2...v3.5.1-beta.3) (2023-11-14)


### Bug Fixes

* 🐝 Jellyfin users now can have uppercase usernames ([1539c56](https://github.com/Wizarrrr/wizarr/commit/1539c56b617c3fce0d17877c960a73fd8e6a1aac))
* 🩹 fix workflow issue ([268aeeb](https://github.com/Wizarrrr/wizarr/commit/268aeeb33e6e8fb79c81dfe74b0868fbb7128e1b))

## [3.5.1-beta.3](https://github.com/Wizarrrr/wizarr/compare/v3.5.1-beta.2...v3.5.1-beta.3) (2023-11-14)


### Bug Fixes

* 🐝 Jellyfin users now can have uppercase usernames ([1539c56](https://github.com/Wizarrrr/wizarr/commit/1539c56b617c3fce0d17877c960a73fd8e6a1aac))

## [3.5.1-beta.2](https://github.com/Wizarrrr/wizarr/compare/v3.5.1-beta.1...v3.5.1-beta.2) (2023-11-09)


### Bug Fixes

* 🐝 beta-ci workflow ([6044747](https://github.com/Wizarrrr/wizarr/commit/60447477eb1dc932013e986db4e91a8c827311cf))
* 🚑 beta-ci workflow ([bc7d834](https://github.com/Wizarrrr/wizarr/commit/bc7d834f83736bf762cb0315c19c6badd9b2fc89))
