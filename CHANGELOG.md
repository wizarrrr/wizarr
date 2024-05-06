## [4.1.0](https://github.com/wizarrrr/wizarr/compare/v4.0.0...v4.1.0) (2024-05-05)


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
* **release:** 4.1.0-beta.1 ([b4d5a34](https://github.com/wizarrrr/wizarr/commit/b4d5a34a1f1e93ab41e3420d367754c6b5e1db5a)), closes [#397](https://github.com/wizarrrr/wizarr/issues/397)


### Documentation

* 📚 removed v3 mentions from root readme ([d7a4495](https://github.com/wizarrrr/wizarr/commit/d7a44950563139106e18e81ea433f654852b62af))


### Code Refactoring

* 🔧 Change the admin login to reflect the new homepage ([549b3de](https://github.com/wizarrrr/wizarr/commit/549b3def461fdb07075a36a88f44ed1f198dc74e))
* 🔧 Cleanup old deprecated code ([fa56308](https://github.com/wizarrrr/wizarr/commit/fa56308bbb428f0c117a738660c94a81510fd1b8))
* 🔧 Removed ability to fetch profile picture from media servers ([e3ab547](https://github.com/wizarrrr/wizarr/commit/e3ab5475e43388fca753128e00d3722b2f735181))
* 🔨 Changed profile picture logic for media servers ([f1f94e1](https://github.com/wizarrrr/wizarr/commit/f1f94e1e64c0b49c73a037072387b9dbbf6eefa6))

## [4.0.0](https://github.com/wizarrrr/wizarr/compare/v3.5.1...v4.0.0) (2024-04-29)


### ⚠ BREAKING CHANGES

* begin 4.x.x versioning

### New Features

* ✨ :sparkles: Emby users can now set max streams ([3b0d4e0](https://github.com/wizarrrr/wizarr/commit/3b0d4e003d2e40a59cbd8c52f3cb4d0b868cecb7))
* 🎉 :sparkles: Added Emby Support ([c882992](https://github.com/wizarrrr/wizarr/commit/c882992bda7799b97f98c6c4f6fd0e4d7d4e7db7))
* 🎉 :sparkles: Scanning in Emby users now attaches connect email as user email ([46d6f22](https://github.com/wizarrrr/wizarr/commit/46d6f226b0cc09713fec0d4e107ed6f4e67e59a9))
* 🎉 Live TV can now be enabled/disabled for Jellyfin/Emby invites ([8723d1c](https://github.com/wizarrrr/wizarr/commit/8723d1ce34cc7159ddef014837d54cd9afb307ff))
* 🎊 :sparkles: Emby and Jellyfin now update username/email on an updated scan ([7c158ca](https://github.com/wizarrrr/wizarr/commit/7c158caaec967e0863ba3f5ced73dca21ef1047e))
* 🚑 added ability to specify concurrent sessions on jellyfin ([#378](https://github.com/wizarrrr/wizarr/issues/378)) ([062bc6b](https://github.com/wizarrrr/wizarr/commit/062bc6b5e0fa791d28973933c7752f54348cb0f8)), closes [#377](https://github.com/wizarrrr/wizarr/issues/377)
* finshed backend password change ([5b1ce2e](https://github.com/wizarrrr/wizarr/commit/5b1ce2e9818cbc8b393623f6642a7b3f4b832e65))
* password reset frontend done, backend started ([d15e0a1](https://github.com/wizarrrr/wizarr/commit/d15e0a1660ef67e5ac294fc375ae989a7d362db8))
* **wizarr-frontend:** 🚀 Add extended labels to buttons ([72c7dc4](https://github.com/wizarrrr/wizarr/commit/72c7dc4f11ad0ff8d2dba3b47071163bc269f4e0))


### Bug Fixes

* 🐛 :bug: Fixed issue where Emby/Plex would error on creating an invite ([eb54d32](https://github.com/wizarrrr/wizarr/commit/eb54d326e5d6add26fb705cb19448f32e12574c1))
* 🐛 :memo: Fix the form being the wrong namr ([602d5d1](https://github.com/wizarrrr/wizarr/commit/602d5d1b2d41152316efd3d13e0c92f2310959f1))
* 🐛 refactor server_api.py and software_lifecycle.py for better exception handling ([8cf2b32](https://github.com/wizarrrr/wizarr/commit/8cf2b329a8aeb4a27b783a454a2a58e02230e294))
* 🐝 :bug: Remove trailing slashes on server URL's ([c4cfd77](https://github.com/wizarrrr/wizarr/commit/c4cfd77f5741fb4a25006948e5facc016c76ddc2))
* 🐝 Corrected Live TV for Jellyfin ([1b94a6e](https://github.com/wizarrrr/wizarr/commit/1b94a6eaee7205350a22b53ebf61af2d0e620c61))
* 🐝 update toast can now be dismissed ([f2585ca](https://github.com/wizarrrr/wizarr/commit/f2585ca30c5e200e7cffb03abe7bf853db2f56a9))
* 🩹 :art: Resolved scaling of theme selector on help wizard ([ccf75fc](https://github.com/wizarrrr/wizarr/commit/ccf75fc91069a7ffc05d078a75fd3cfcb40c3940))
* 🩹 :bug: Fixed copy server URL when override set ([ab5e680](https://github.com/wizarrrr/wizarr/commit/ab5e6804a3f054a48595dc187158ad7a309cb5b3))
* 🩹 :bug: Fixed issue where Jellyseerr could not be selected for Emby servers ([83c381a](https://github.com/wizarrrr/wizarr/commit/83c381a0707fdcbf31f2ee101c5fa405edd9bec6))
* 🩹 :fire: Removed remaining label ([268fda9](https://github.com/wizarrrr/wizarr/commit/268fda9612584591b50926409c0e8b9be57449bc))
* 🩹 change delete user call to emby function ([139cf86](https://github.com/wizarrrr/wizarr/commit/139cf86053198efa1c9f800cb414998a416a2852))
* 🩹 Default Live TV checkbox to enabled to reflect Jellyfin/Emby default ([1cba8c3](https://github.com/wizarrrr/wizarr/commit/1cba8c3fea60c8962aea6570e8984b79069ab518))
* 🩹 Fixed error which occured when using LDAP ([1ba2e0a](https://github.com/wizarrrr/wizarr/commit/1ba2e0a1246cb58785665dfa3954f83ee883c285))
* **backend:** user sync error on plex managed/guest users ([#357](https://github.com/wizarrrr/wizarr/issues/357)) ([1467046](https://github.com/wizarrrr/wizarr/commit/146704609d64ba13d1c8a7d80a80fd09e55bfd50))
* **discord-release-alert:** 🐛 mentions failing in embeded payload ([8e87c41](https://github.com/wizarrrr/wizarr/commit/8e87c414a9d333e0c9dcf0722d794b83658e5d08))
* **frontend:** 🐛 users without token no longer cause error on scan ([#344](https://github.com/wizarrrr/wizarr/issues/344)) ([05ce4f5](https://github.com/wizarrrr/wizarr/commit/05ce4f5de529993f2cbfc35439f27ddb7933fa73))
* **frontend:** cant remove discord widget id ([#347](https://github.com/wizarrrr/wizarr/issues/347)) ([fefcb06](https://github.com/wizarrrr/wizarr/commit/fefcb065486c9ec7809167744867c66034df208a))
* remove latest info widget ([#353](https://github.com/wizarrrr/wizarr/issues/353)) ([37e21fe](https://github.com/wizarrrr/wizarr/commit/37e21fe98562ec1a9bfec971b251a8a68f429d70))
* **wizarr-backend:** 🚑 added password strength test ([ff83c30](https://github.com/wizarrrr/wizarr/commit/ff83c30302ee44c9113d1419b15358b85b1d8cc9))


### Performance Improvements

* 🚀 :sparkles: Changed to use floating vue ([ce0b92f](https://github.com/wizarrrr/wizarr/commit/ce0b92f6359fda7d470033551b4ee68ab3915e40))
* **test:** changelog ([7eacd08](https://github.com/wizarrrr/wizarr/commit/7eacd0820d5c7044378f7247b8b8228911738786))


### Build System

* **deps:** 🔨 🏗️ update browserslist to latest ([b9b95bc](https://github.com/wizarrrr/wizarr/commit/b9b95bc45c091570a99b75b401f92579807db3ca))
* **npm:** add conventionalcommit changelog package ([633868a](https://github.com/wizarrrr/wizarr/commit/633868acbce4f8e5e92c2a9871bbef52dd8a990b))
* **semantic-release:** 👷 add explict typing for changelog ([62ef792](https://github.com/wizarrrr/wizarr/commit/62ef7927f7f96a70c6b77d5e19ff455853dc14ca))
* **semantic-release:** 👷 update discord webhook payload to [@dev-updates](https://github.com/dev-updates) ([d0886bf](https://github.com/wizarrrr/wizarr/commit/d0886bfb2da5132e595ac9a9c6b3afc18bb0cd53))
* **semantic-release:** 🧱 add other commit types to changelog ([6b49b2a](https://github.com/wizarrrr/wizarr/commit/6b49b2af17b9f197c6845e0b70ed6c25088812e8))
* **semantic-release:** use conventioncommits preset ([582982f](https://github.com/wizarrrr/wizarr/commit/582982fe714211d095993b2d6310530b7ec1256b))
* **test:** changelog ([54955f5](https://github.com/wizarrrr/wizarr/commit/54955f54aee96709cb4d50c8ba649e4db5c854cd))


### Continuous Integration

* 🔧 auto merge release branch back into beta ([43b4c9d](https://github.com/wizarrrr/wizarr/commit/43b4c9d04574e974b4f1a2f16c1f02edbe5e476f))
* 🔧 fix missing apostrophe causing action fail ([429b4f6](https://github.com/wizarrrr/wizarr/commit/429b4f6659d193429c2bb3eba42414d88d1c6434))
* 🔧 update action naming to better align with workflow ([a7ab17a](https://github.com/wizarrrr/wizarr/commit/a7ab17a06146780695eefcacb2cd025e16800a13))
* 🧪 fix nightly action name ([291cb18](https://github.com/wizarrrr/wizarr/commit/291cb1877540f8db5654c4bf9b48e0dd1310f446))
* 🧪 nightly image builds off develop branch ([05d5331](https://github.com/wizarrrr/wizarr/commit/05d5331ee3b96fd3174d5d67b1078e48884e3365))
* **semantic-release:** 🔧 explicity define breaking changes ([b144ff2](https://github.com/wizarrrr/wizarr/commit/b144ff21185fc2c4699d75b1631339e4c240985d))
* **test:** changelog ([24e565f](https://github.com/wizarrrr/wizarr/commit/24e565f4014e7fc7397c6bdee2b2b13604d899c5))


### Chores

* 🧹 bump db migration script version/date ([a71ada5](https://github.com/wizarrrr/wizarr/commit/a71ada5126c78a6cdb772d46aa355c9a4c2c5546))
* 🧺 :pencil2: Fixed a type with the setup finalisation ([00d6143](https://github.com/wizarrrr/wizarr/commit/00d6143986d1564a40d276cc7a083a828e5ca4c5))
* 🧽 add unRaid support ([71c00e1](https://github.com/wizarrrr/wizarr/commit/71c00e189d77105ba7c05cb8ebc2d4e9ad118968))
* 🧽 fix versioning file ([66cef97](https://github.com/wizarrrr/wizarr/commit/66cef9765dae0a67f26fa64ef1a73687e3cb5b77))
* 🧽 remove changelog test file ([3191b0a](https://github.com/wizarrrr/wizarr/commit/3191b0a0c59bd4ba89c4684d5e9bf1641c970ebf))
* 🧽 update visibility of hidden beta items ([f44ea0b](https://github.com/wizarrrr/wizarr/commit/f44ea0b4341c2f123a5b23e6c37c9031f0622ce5))
* clean up unused refrences ([7b97be4](https://github.com/wizarrrr/wizarr/commit/7b97be4d8a21649c7ec7c524024280883d9a16f1))
* **gitignore:** add nvm versioning file ([daa8e6c](https://github.com/wizarrrr/wizarr/commit/daa8e6cf39414c37945b13254591153835e3c37b))
* **release:** 3.5.1-beta.7 ([3a26ead](https://github.com/wizarrrr/wizarr/commit/3a26ead6563c789faaa5682a488884b5d876b166))
* **release:** 4.0.0-beta.1 ([3a90b8d](https://github.com/wizarrrr/wizarr/commit/3a90b8d1a3af6141d0dccf6f6a04f8cfde57ce70)), closes [#357](https://github.com/wizarrrr/wizarr/issues/357) [#344](https://github.com/wizarrrr/wizarr/issues/344) [#347](https://github.com/wizarrrr/wizarr/issues/347) [#353](https://github.com/wizarrrr/wizarr/issues/353)
* **release:** 4.0.0-beta.2 ([d6bd390](https://github.com/wizarrrr/wizarr/commit/d6bd39001e88c829ae9aec1ac2deabf79fde96c8))
* **release:** 4.0.0-beta.3 ([709e009](https://github.com/wizarrrr/wizarr/commit/709e0097c817c28580c5d17d88d75162bb264463))
* **release:** 4.0.0-beta.4 ([6e9ba8d](https://github.com/wizarrrr/wizarr/commit/6e9ba8d91ede69087ddb474e871549a68fdddca7))
* **release:** 4.0.0-beta.5 ([a74aafd](https://github.com/wizarrrr/wizarr/commit/a74aafdd62ea9e6538401fa3a52157055652b7d6))
* **release:** 4.0.0-beta.6 ([9dc466a](https://github.com/wizarrrr/wizarr/commit/9dc466a15b5d7ca450235d308e465cc795700739))
* **release:** 4.0.0-beta.7 ([cd74551](https://github.com/wizarrrr/wizarr/commit/cd745511690599114026a7d04e3c1307489d446b))
* **release:** 4.0.0-beta.8 ([0f5d8e0](https://github.com/wizarrrr/wizarr/commit/0f5d8e09fa4159ea5517b8b85ffccf1c140db7b1)), closes [#377](https://github.com/wizarrrr/wizarr/issues/377)
* **release:** 4.0.0-beta.9 ([724755e](https://github.com/wizarrrr/wizarr/commit/724755ef40b011856e689f526617934521e6be18))
* start of v4 development 🎆🎆 ([80e95dc](https://github.com/wizarrrr/wizarr/commit/80e95dc0fdde4c04d3175f6fb863c12c8cb5bbd3))
* **translations:** 🧺 extract strings ([a96a18f](https://github.com/wizarrrr/wizarr/commit/a96a18fef6a3eb9c9e7637250103fbeec8300980))
* **workspace:** 🧹 add commit editor extension and config ([423c59c](https://github.com/wizarrrr/wizarr/commit/423c59ca88ca6dc2bdb0c7a677f655f6da4c34a8))
* **workspace:** 🧺 add nx console extension ([7bc90d1](https://github.com/wizarrrr/wizarr/commit/7bc90d1c3c18c9e843854c54ca48c8971615ccdb))


### Documentation

* 📖 :memo: Corrected grammatical issues with Download page on Jellyfin ([0ba2a78](https://github.com/wizarrrr/wizarr/commit/0ba2a78aa93c9f0616f81fb620a1a7ef581f66b8))
* 📚 :memo: Fixed Emby showing in the Jellyfin download page ([4302699](https://github.com/wizarrrr/wizarr/commit/43026990eb3a1254ad08104c75a96d291382c2a6))
* 📚 refactor portions of contribution guide ([07ae431](https://github.com/wizarrrr/wizarr/commit/07ae4311ab776fdeaba1ba1e571deefb1284a9d5))
* 📚 update build badge for new action names ([a218de1](https://github.com/wizarrrr/wizarr/commit/a218de13df9f2a3ac85d274d375966119337ac0c))
* 📝 create contribution guide in project root dir ([619a97b](https://github.com/wizarrrr/wizarr/commit/619a97b2be9523acb97276af6f27b5789e11fb72))
* added warning against modifying the $server_name variable ([e27f375](https://github.com/wizarrrr/wizarr/commit/e27f3754f93482df930ee2fe1058078963fa81fa))
* readme/setup/unraid refactor ([#364](https://github.com/wizarrrr/wizarr/issues/364)) ([afc180d](https://github.com/wizarrrr/wizarr/commit/afc180dd5e547abd9f157be6bf79449981faa60f))
* **readme:** 📚 update discord release channel ([7d8afc9](https://github.com/wizarrrr/wizarr/commit/7d8afc9cb6d0d21baaeaa7db5da3cc85b655d286))
* **readme:** fix build badge ([97116ee](https://github.com/wizarrrr/wizarr/commit/97116ee5efa5188f4e59e1a6e133a7ae7d1db1da))
* refactor contribution guide ([642b3cd](https://github.com/wizarrrr/wizarr/commit/642b3cd8cf815318f16d055736884dfdd462a252))
* **test:** changelog ([a09f31c](https://github.com/wizarrrr/wizarr/commit/a09f31ccdd97ca2738eb9ec0874c6ead420c4c6c))
* **test:** changelog ([4a479e5](https://github.com/wizarrrr/wizarr/commit/4a479e5e994cdbf8fe29c73b834c578763866bcf))


### Style Changes

* 🎨 new wizarr logo/branding ([#361](https://github.com/wizarrrr/wizarr/issues/361)) ([864a3df](https://github.com/wizarrrr/wizarr/commit/864a3dfc6e69ec2faa7ed354bef4360231b5f303))
* 💎 minor corrections to discord alert payload ([c03c2cf](https://github.com/wizarrrr/wizarr/commit/c03c2cf2750e1e6c7e70bca46d56ac1fbe9094f2))
* 💎 simplify image tag condition ([8930479](https://github.com/wizarrrr/wizarr/commit/893047977c744d6d3b0d1f7a2103df3e31051c02))
* add specifc image tag targeting beta/latest ([71da180](https://github.com/wizarrrr/wizarr/commit/71da180731eec9f79d5ead5b1e8def3cc17a3135))
* another correction for the backticks ([428fec7](https://github.com/wizarrrr/wizarr/commit/428fec715190991e321469dd4d2c4be15ee8f622))
* backticks corrected ([eb4259a](https://github.com/wizarrrr/wizarr/commit/eb4259a235d7a319dd340c86223385c53cf81ca4))
* **discord-webhook:** 🎨 role mentions for new channel structure ([2c30e4c](https://github.com/wizarrrr/wizarr/commit/2c30e4c8fa0c32df439f5ca21140381e566aa8ef))
* fix apostrophe usage ([3be097c](https://github.com/wizarrrr/wizarr/commit/3be097c8de1f50fc9efbe448d47d665618dd2b23))
* fix backticks reaking payload formatting ([0ebf1c7](https://github.com/wizarrrr/wizarr/commit/0ebf1c7bacf81fef88fba9d9fc63de2d12c7a99f))
* removed an extra space ([c96e72e](https://github.com/wizarrrr/wizarr/commit/c96e72e4bedbaaec782e9cedc839d078f470082b))
* simplify image tag statement check ([96a18ae](https://github.com/wizarrrr/wizarr/commit/96a18ae5754f725380cfee27a4cc85ba119b3369))
* **test:** changelog ([463db02](https://github.com/wizarrrr/wizarr/commit/463db0299a5c01b35ba1c523199a046f45c94506))
* update discord webhook message ([d8310a7](https://github.com/wizarrrr/wizarr/commit/d8310a74b06644b59c4907d5ae1b19637cfa196c))
* Updated logo with mustache ([#363](https://github.com/wizarrrr/wizarr/issues/363)) ([86827b3](https://github.com/wizarrrr/wizarr/commit/86827b33fd7c290616344b048b9912599620c6f1))


### Code Refactoring

* 📦 :lipstick: Added password meter to new password field ([e35680a](https://github.com/wizarrrr/wizarr/commit/e35680a0427908f4be12c6edc6bdf678457a94c7))
* 📦 :zap: Remove membership and live chat ([3b08550](https://github.com/wizarrrr/wizarr/commit/3b085502a6ff846aedb82cd8d36834a34bce2399))
* 📦 added tooltip to scan server in media server settings ([2fdfab2](https://github.com/wizarrrr/wizarr/commit/2fdfab28f35e2d1b57b8fb2c322cc392bf3165ea))
* 📦 hiding unimplemented features ([5c7082f](https://github.com/wizarrrr/wizarr/commit/5c7082f757936c0fd0229ebbda9fbf3b317b76f7))
* 🔧 :memo: Added warning about open collective ([ae29be3](https://github.com/wizarrrr/wizarr/commit/ae29be356716fc862c4eb063ac74cada14abd150))
* 🔧 add e2e workspace, exclude apps dir ([12054f7](https://github.com/wizarrrr/wizarr/commit/12054f771cc31ac7e517927e19bdf8e9d1b2f432))
* 🔧 moved password to account page ([dfc6490](https://github.com/wizarrrr/wizarr/commit/dfc649043a88e775c9b3db1124d6d92f6b6c5368))
* 🔧 spelling and grammatical corrections ([9eb591f](https://github.com/wizarrrr/wizarr/commit/9eb591fa3730513e3ff8e99bafb8344f7647ed3f))
* 🔨 added tooltip to request access button ([3d576a4](https://github.com/wizarrrr/wizarr/commit/3d576a45b455723c04ed92edc7a69b32232ca9c8))
* **test:** changelog ([7e2aacd](https://github.com/wizarrrr/wizarr/commit/7e2aacd315060d88c62cce7e0b479219f7979600))
* **test:** changelog ([9370752](https://github.com/wizarrrr/wizarr/commit/9370752b30e9f2859c0a7373c6313c8fb436809e))
* update nginx values on docs ([d7e52a9](https://github.com/wizarrrr/wizarr/commit/d7e52a9aba3011b765cfdb993d098e5dbaaf8af4))
* **workspace:** 🔧 update dev workspace and sorting ([9c2561a](https://github.com/wizarrrr/wizarr/commit/9c2561aa8c447b42982e22a5220fd74d9c34c8cc))

## [3.5.1](https://github.com/wizarrrr/wizarr/compare/v3.5.0...v3.5.1) (2023-11-17)


### Bug Fixes

* 🐝 beta-ci workflow ([6044747](https://github.com/wizarrrr/wizarr/commit/60447477eb1dc932013e986db4e91a8c827311cf))
* 🐝 Jellyfin users now can have uppercase usernames ([1539c56](https://github.com/wizarrrr/wizarr/commit/1539c56b617c3fce0d17877c960a73fd8e6a1aac))
* 🔧 release branch identification logic and improve error handling ([e963e0b](https://github.com/wizarrrr/wizarr/commit/e963e0beec90c5d476231e1e149451480342c5d7))
* 🩹 add formkit stories ([e5cd97b](https://github.com/wizarrrr/wizarr/commit/e5cd97ba0c7c9dcf79ab8c59d888e8e8a326671f))
* 🩹 fix workflow issue ([268aeeb](https://github.com/wizarrrr/wizarr/commit/268aeeb33e6e8fb79c81dfe74b0868fbb7128e1b))
* 🩹 software lifecycle issue ([15b1edf](https://github.com/wizarrrr/wizarr/commit/15b1edf21ca43086346555f8afa2ac375f303e86))
* 🚑 beta-ci workflow ([bc7d834](https://github.com/wizarrrr/wizarr/commit/bc7d834f83736bf762cb0315c19c6badd9b2fc89))
* 🚑 software lifecycle issue ([ac55841](https://github.com/wizarrrr/wizarr/commit/ac55841b892653d62eda2b3951bf04527b1b4349))
* 🆘 EMERGENCY FIX FOR VERSION 🆘 ([7570ec1](https://github.com/wizarrrr/wizarr/commit/7570ec14d327bfad4000184732f4e329df6e0448))

## [3.5.1](https://github.com/wizarrrr/wizarr/compare/v3.5.0...v3.5.1) (2023-11-17)


### Bug Fixes

* 🐝 beta-ci workflow ([6044747](https://github.com/wizarrrr/wizarr/commit/60447477eb1dc932013e986db4e91a8c827311cf))
* 🐝 Jellyfin users now can have uppercase usernames ([1539c56](https://github.com/wizarrrr/wizarr/commit/1539c56b617c3fce0d17877c960a73fd8e6a1aac))
* 🔧 release branch identification logic and improve error handling ([e963e0b](https://github.com/wizarrrr/wizarr/commit/e963e0beec90c5d476231e1e149451480342c5d7))
* 🩹 add formkit stories ([e5cd97b](https://github.com/wizarrrr/wizarr/commit/e5cd97ba0c7c9dcf79ab8c59d888e8e8a326671f))
* 🩹 fix workflow issue ([268aeeb](https://github.com/wizarrrr/wizarr/commit/268aeeb33e6e8fb79c81dfe74b0868fbb7128e1b))
* 🚑 beta-ci workflow ([bc7d834](https://github.com/wizarrrr/wizarr/commit/bc7d834f83736bf762cb0315c19c6badd9b2fc89))
