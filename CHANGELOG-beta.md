## [4.2.0-beta.3](https://github.com/wizarrrr/wizarr/compare/v4.2.0-beta.2...v4.2.0-beta.3) (2024-08-05)


### New Features

* ✨ Allow editing of all onboarding pages ([#471](https://github.com/wizarrrr/wizarr/issues/471)) ([3d4c06a](https://github.com/wizarrrr/wizarr/commit/3d4c06a4450c7f28547a4478f10c5c0907aff013))
* 🎉 Add MAX_CONTENT_LENGTH configuration for file uploads ([#473](https://github.com/wizarrrr/wizarr/issues/473)) ([2edf951](https://github.com/wizarrrr/wizarr/commit/2edf951afbbc2af4d4c4f7222df2207d013edb63))
* 🎉 Add swedish translations ([#475](https://github.com/wizarrrr/wizarr/issues/475)) ([e3b0240](https://github.com/wizarrrr/wizarr/commit/e3b0240bf834535275b65ef5063ec2ec2c3b200d))


### Chores

* 🧽 sync develop with beta ([3de4467](https://github.com/wizarrrr/wizarr/commit/3de4467c9c5204b41f4dead31695efb152fa449a))


### Code Refactoring

* 🛠️ Remove auto PR [skip-ci] ([d57e726](https://github.com/wizarrrr/wizarr/commit/d57e726f91f7cbd5c311845cf7071e2cf946fdb4))

## [4.2.0-beta.2](https://github.com/wizarrrr/wizarr/compare/v4.2.0-beta.1...v4.2.0-beta.2) (2024-08-02)


### New Features

* 🎊 Any length of invitation code ([#469](https://github.com/wizarrrr/wizarr/issues/469)) ([c850c8e](https://github.com/wizarrrr/wizarr/commit/c850c8e64a34cf7fcee584e6a20a2b801830a74b))


### Bug Fixes

* 🐛 Solve issue reordering onboarding pages ([2f6ca87](https://github.com/wizarrrr/wizarr/commit/2f6ca87e106eb83e0c81fb90666546bb43c2280a))
* 🐛 Solve some issues with markdown preview ([#470](https://github.com/wizarrrr/wizarr/issues/470)) ([2051990](https://github.com/wizarrrr/wizarr/commit/2051990271cd0dfee3efad8b641065513ee4e479))

## [4.2.0-beta.1](https://github.com/wizarrrr/wizarr/compare/v4.1.1...v4.2.0-beta.1) (2024-07-31)


### New Features

* ✨ Added Onboarding Customisation ([e6e9d68](https://github.com/wizarrrr/wizarr/commit/e6e9d6890b431ce6ec60e33306d28f3a3a571a98))
* 🎊 Make DefaultButton center icon ([#462](https://github.com/wizarrrr/wizarr/issues/462)) ([c8b8d36](https://github.com/wizarrrr/wizarr/commit/c8b8d3653b140472172737ec275d6444054b2ada))
* Ability to specify whether a user can download content ([#449](https://github.com/wizarrrr/wizarr/issues/449)) ([10e104b](https://github.com/wizarrrr/wizarr/commit/10e104b80fd3d2ae53678c0d83a4044d5b2deee0))


### Bug Fixes

* 🐛 Solve security alerts ([#465](https://github.com/wizarrrr/wizarr/issues/465)) ([7a958fe](https://github.com/wizarrrr/wizarr/commit/7a958fe83e7fbc4feac0a1ae88353c92642d3336))
* 🛠️ Country Code for Sweden being incorrect ([#457](https://github.com/wizarrrr/wizarr/issues/457)) ([2408a59](https://github.com/wizarrrr/wizarr/commit/2408a599a49a9a86a8ed4eda1284c4fa48ef6d35))


### Continuous Integration

* **build-image:** 🧪 bump upload-artifact version ([c6b8573](https://github.com/wizarrrr/wizarr/commit/c6b85739c3f69a1d1e986fd7a5a06e1d0dfc52cb))
* **build-image:** 🧪 drop download/upload artifact version ([0b711e1](https://github.com/wizarrrr/wizarr/commit/0b711e1cd1031ab614253373e40e1819dcd74cad))
* **code-ql:** 🧪 add beta and master branch ([357e067](https://github.com/wizarrrr/wizarr/commit/357e067369a58c01eb4be63390c6b6d911d2681a))
* **dependabot:** 🔧 fix pip path ([1147e44](https://github.com/wizarrrr/wizarr/commit/1147e4496f1300a063c1826b844545c4cfee934d))


### Chores

* 🧽 sync develop with beta ([1a263de](https://github.com/wizarrrr/wizarr/commit/1a263de76e4bf3cc10025e6d5f421424fb869584))
* 🧽 sync develop with master ([e2b8fd4](https://github.com/wizarrrr/wizarr/commit/e2b8fd4549424b103f4d87f6ca057d7e7349ad5d))
* **deps:** bump actions/checkout from 2 to 4 ([#431](https://github.com/wizarrrr/wizarr/issues/431)) ([4b77632](https://github.com/wizarrrr/wizarr/commit/4b776320e7bd9e7d5c6ae40dbe2515c66a978c48))
* **deps:** bump actions/download-artifact from 3 to 4 ([#428](https://github.com/wizarrrr/wizarr/issues/428)) ([92c7154](https://github.com/wizarrrr/wizarr/commit/92c7154e8c6ba9614efe0d2b4652fc08faeea8f1))
* **deps:** bump actions/setup-python from 4 to 5 ([#430](https://github.com/wizarrrr/wizarr/issues/430)) ([0d66052](https://github.com/wizarrrr/wizarr/commit/0d660528f88a390160b43db95be7182376ec743c))
* **deps:** bump docker/build-push-action from 5 to 6 ([#446](https://github.com/wizarrrr/wizarr/issues/446)) ([9780190](https://github.com/wizarrrr/wizarr/commit/9780190169d7f9f34aabc603ac5eb0e665c96178))
* **deps:** bump getsentry/action-github-app-token from 2 to 3 ([#432](https://github.com/wizarrrr/wizarr/issues/432)) ([8c026d2](https://github.com/wizarrrr/wizarr/commit/8c026d269dbee9b654db28681d0220187a0ac52d))
* **deps:** bump peaceiris/actions-gh-pages from 3 to 4 ([#429](https://github.com/wizarrrr/wizarr/issues/429)) ([fdf96e5](https://github.com/wizarrrr/wizarr/commit/fdf96e563d2017bfcb2d2ba178f9152e57016a55))
* **deps:** bump the pip group across 1 directory with 7 updates ([#433](https://github.com/wizarrrr/wizarr/issues/433)) ([8ec9ddc](https://github.com/wizarrrr/wizarr/commit/8ec9ddc594752fb788da28e42ae2759cc7eab3e6))
* **deps:** bump tj-actions/branch-names from 7 to 8 ([#435](https://github.com/wizarrrr/wizarr/issues/435)) ([c0e7c2a](https://github.com/wizarrrr/wizarr/commit/c0e7c2a0878da7b9423c2dec9c36771bca9ee657))


### Code Refactoring

* 📦 Cleanup code for darkmode ([#458](https://github.com/wizarrrr/wizarr/issues/458)) ([856fa34](https://github.com/wizarrrr/wizarr/commit/856fa349acd4b1e4b5e784e0b7b1014d766cdcf3))

## [4.1.1-beta.3](https://github.com/wizarrrr/wizarr/compare/v4.1.1-beta.2...v4.1.1-beta.3) (2024-05-19)


### Bug Fixes

* 🚑 Plex API endpoint for deleting users ([462deae](https://github.com/wizarrrr/wizarr/commit/462deae0f8d3e3c77a8d33f43382abeba8dfa218))


### Chores

* 🧽 sync develop with beta ([7107159](https://github.com/wizarrrr/wizarr/commit/7107159ce9bfa8e54952696a53abc37a3f2ba13a))

## [4.1.1-beta.2](https://github.com/wizarrrr/wizarr/compare/v4.1.1-beta.1...v4.1.1-beta.2) (2024-05-19)


### Continuous Integration

* **codeql:** setup code vulnerability scanning ([#417](https://github.com/wizarrrr/wizarr/issues/417)) ([37612b5](https://github.com/wizarrrr/wizarr/commit/37612b527084a2e7c1074cc5699bb0e8434b6a30))
* **deps:** setup dependabot updates ([#413](https://github.com/wizarrrr/wizarr/issues/413)) ([97a5fd4](https://github.com/wizarrrr/wizarr/commit/97a5fd42727bb879c1fc391e9ff46723c3a9ce34))
* **pr-review:** 🔧 scope to pr target only ([e6008a6](https://github.com/wizarrrr/wizarr/commit/e6008a65d840872c0066443190043307fe2f5d92))
* setup auto pr reviews ([#415](https://github.com/wizarrrr/wizarr/issues/415)) ([ec0c1ee](https://github.com/wizarrrr/wizarr/commit/ec0c1ee91687a942a7ac54a731b84fc43cb9c9d1))


### Chores

* 🧽 sync develop with beta ([3e213b1](https://github.com/wizarrrr/wizarr/commit/3e213b1920ee56e7915acc69ce1192f2fc0ae278))

## [4.1.1-beta.1](https://github.com/wizarrrr/wizarr/compare/v4.1.0...v4.1.1-beta.1) (2024-05-06)


### Bug Fixes

* 🐛 Beta message no longer shows on main releases ([819223e](https://github.com/wizarrrr/wizarr/commit/819223e0b7dd419926946667c5e83837ef586052))
* 🐛 Fix migration syntax error ([affa9ff](https://github.com/wizarrrr/wizarr/commit/affa9ffe130f4100df61d2cf93a061a3f523be70))
* 🩹 Re-write plex.tv URL's to app.plex.tv on media server override ([7eaf403](https://github.com/wizarrrr/wizarr/commit/7eaf403044b0563ccfe5423b9ca262ba526750e9))
* 🩹 Removed plex home configuration due to not existing in the Plex API ([a075079](https://github.com/wizarrrr/wizarr/commit/a07507929a8c747787577015693eefeffc8ce658))
* 🚑 Corrected the variable for unlimited invite uses on plex ([b605010](https://github.com/wizarrrr/wizarr/commit/b605010b371bfd754f7b5406fe7aec74c0337adb))


### Performance Improvements

* 🚀 Only update Emby/Jellyfin users when data is different ([44fe2f1](https://github.com/wizarrrr/wizarr/commit/44fe2f1c2a3dd583fb4daa8c2563167f6b34a459))
* 🚀API Endpoint Optimisation ([#409](https://github.com/wizarrrr/wizarr/issues/409)) ([82d4cf5](https://github.com/wizarrrr/wizarr/commit/82d4cf5b4ffbb08669bfe955cb833a3d4c65756b))


### Continuous Integration

* **semantic-release:** auto-sync commit message ([05b3931](https://github.com/wizarrrr/wizarr/commit/05b3931de119ae27c625bbdb7871cab63d5abe0d))
* **semantic-release:** update sync commit msg ([9235de4](https://github.com/wizarrrr/wizarr/commit/9235de4095dfde158f8f52376ea0fc4fc7abd06f))


### Chores

* 🧺 Exclude unraid template from triggering semantic releases ([08840b9](https://github.com/wizarrrr/wizarr/commit/08840b9056e32649ab943ec473b3b71e6c8ed7d8))
* 🧼 Corrected branch of the latest image ([3e52988](https://github.com/wizarrrr/wizarr/commit/3e5298879b794df30d91a13bf53fa78a2fee6fd1))
* 🧼 Exclude language filles from the workspace search ([e956c28](https://github.com/wizarrrr/wizarr/commit/e956c2838c4b76f601cc4b21cbe03802a3da32a8))
* 🧽 Fixed formatting with sematic release commit names ([c913942](https://github.com/wizarrrr/wizarr/commit/c913942d5685fb77134e92a2c6f4a580431d053b))
* 🧽 Updated the unraid template to include different branches ([8a82a78](https://github.com/wizarrrr/wizarr/commit/8a82a78944e7efac2284142df9a03446c51d909e))


### Code Refactoring

* 📦 Update Available toasts no longer appear for non-admins ([8f18d98](https://github.com/wizarrrr/wizarr/commit/8f18d98a718d6a541919f3f81c77d314bab0e88f))

## [4.1.0-beta.1](https://github.com/wizarrrr/wizarr/compare/v4.0.0...v4.1.0-beta.1) (2024-05-03)


### New Features

* ✨ Replaced the default homepage with the invite interface ([9c6ea38](https://github.com/wizarrrr/wizarr/commit/9c6ea387984dcfa750842c7ad578b3835f43c1f9))
* ✨Ability to specify whether a user displays on login page ([#397](https://github.com/wizarrrr/wizarr/issues/397)) ([a1380e0](https://github.com/wizarrrr/wizarr/commit/a1380e0d5d7e6e429f591392e8e21fda220c3d83))


### Bug Fixes

* 🐛 Change live_tv to a boolean through the migration script ([00372cc](https://github.com/wizarrrr/wizarr/commit/00372cccb9365aa6cdd89bc22c4236eb800cc2ea))
* 🐛 Live TV boolean changes to True by default ([e41b935](https://github.com/wizarrrr/wizarr/commit/e41b935c612ea70ed29ab7b97ee3b59a1878f145))
* 🐛 Potential fix for white pages and pages caching ([65feec9](https://github.com/wizarrrr/wizarr/commit/65feec92c9cfe43d67ea8a47fd77d20b26aa7098))
* 🐝 remove extra return statement ([331be20](https://github.com/wizarrrr/wizarr/commit/331be20b6cbdd9c42eac3a785b562dc068c1a8a9))
* 🩹 cast current version as string ([4490590](https://github.com/wizarrrr/wizarr/commit/4490590657f4374d05914f5105863ea1aa46275b))
* 🩹 Disabled access to Live TV Management for Jellyfin/Emby ([a603d56](https://github.com/wizarrrr/wizarr/commit/a603d56a9ae29c486643e3d4d4abf0038b1fff6e))
* 🩹 Fixed plex profile pictures erroring out when Plex Home users are present ([a1c3571](https://github.com/wizarrrr/wizarr/commit/a1c3571b621d0e14d4e75562983622d51620e309))
* 🩹 Import error for software_lifecycle ([f6f9ef9](https://github.com/wizarrrr/wizarr/commit/f6f9ef9fecb70c3a16f2cf967bbbbaa5a6887b14))
* 🚑 Change migration script to a boolean for hide_user ([dec8103](https://github.com/wizarrrr/wizarr/commit/dec810338492a9231fc87041099d2439d21d1160))
* 🚑 Changed order of Emby user password creation ([fd52649](https://github.com/wizarrrr/wizarr/commit/fd52649108911d52f0560c08e8e4f5ad9c70acb4))
* 🚑 Solved issue with the routes clashing ([c3af54e](https://github.com/wizarrrr/wizarr/commit/c3af54ef5e53418691d656d6a81752bd82833a0a))
* **sentry:** 🐛 set release version for proper tracking ([0f4d08c](https://github.com/wizarrrr/wizarr/commit/0f4d08c3afa0c991543904ec3a248032c8fadef1))


### Chores

* 🧺 Changed request service URL field to correctly reflect the service ([553c78f](https://github.com/wizarrrr/wizarr/commit/553c78fa59ba238c2e87d0b569c196a8c6f8bc31))
* 🧺 Remove version getter as not needed ([50957bc](https://github.com/wizarrrr/wizarr/commit/50957bcd0ff950a85e5a8d781fe14e8da42f5c7b))


### Documentation

* 📚 removed v3 mentions from root readme ([d7a4495](https://github.com/wizarrrr/wizarr/commit/d7a44950563139106e18e81ea433f654852b62af))


### Code Refactoring

* 🔧 Change the admin login to reflect the new homepage ([549b3de](https://github.com/wizarrrr/wizarr/commit/549b3def461fdb07075a36a88f44ed1f198dc74e))
* 🔧 Cleanup old deprecated code ([fa56308](https://github.com/wizarrrr/wizarr/commit/fa56308bbb428f0c117a738660c94a81510fd1b8))
* 🔧 Removed ability to fetch profile picture from media servers ([e3ab547](https://github.com/wizarrrr/wizarr/commit/e3ab5475e43388fca753128e00d3722b2f735181))
* 🔨 Changed profile picture logic for media servers ([f1f94e1](https://github.com/wizarrrr/wizarr/commit/f1f94e1e64c0b49c73a037072387b9dbbf6eefa6))

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
