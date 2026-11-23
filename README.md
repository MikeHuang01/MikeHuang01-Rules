# MikeHuang01 规则配置

面向 **QuantumultX** 与 **Shadowrocket** 的去广告、直连与重写规则集。

所有规则文件都由「上游 blackmatrix7 规则 + 本仓库手写规则」自动生成，手写内容只放在两个入口文件里，不会被同步覆盖。

## 一、仓库结构

```text
QuantumultX/
  Direct.list              自动生成  具体域名直连（分流资源，排第 1）
  AdBlock.list             自动生成  去广告与劫持拦截（分流资源，排第 2）
  DirectGeo.list           自动生成  兜底直连：内网网段 / GEOIP / IP-ASN（分流资源，排第 3）
  AdvertisingLite.conf     自动生成  重写资源（rewrite_remote）
  CustomDirect.list        手写维护  ← 只改这里
  targeted-ad-response.js  手写维护  重写用响应脚本
Shadowrocket/
  Direct.conf              自动生成  DOMAIN 语法直连
  AdBlock.conf             自动生成  DOMAIN 语法拦截
  DirectGeo.conf           自动生成  DOMAIN 语法兜底直连
scripts/
  rulelib.py               共享：规则解析、去重、带重试的下载、原子写入
  sync-direct.py           生成 Direct / DirectGeo（QX + Shadowrocket）
  sync-adblock.py          生成 AdBlock（QX + Shadowrocket）
  sync-advertising-lite.py 生成 AdvertisingLite.conf
  check-rules.py           生成后校验（Actions 里跑，本地也能跑）
.github/workflows/sync-direct.yml  每 6 小时同步一次
```

## 二、QuantumultX 导入

### 1. 分流（`[filter_remote]`）—— 三份，顺序不能错

在「设置 → 配置文件 → 分流」中按下面的顺序添加，或者直接粘贴到配置文件的 `[filter_remote]` 段：

```ini
[filter_remote]
https://raw.githubusercontent.com/MikeHuang01/MikeHuang01-Rules/main/QuantumultX/Direct.list, tag=Direct, enabled=true
https://raw.githubusercontent.com/MikeHuang01/MikeHuang01-Rules/main/QuantumultX/AdBlock.list, tag=AdBlock, enabled=true
https://raw.githubusercontent.com/MikeHuang01/MikeHuang01-Rules/main/QuantumultX/DirectGeo.list, tag=DirectGeo, enabled=true
```

| 顺序 | 资源 | 作用 | 为什么必须在这个位置 |
| --- | --- | --- | --- |
| 1 | `Direct.list` | 具体域名直连（HOST / HOST-SUFFIX / HOST-KEYWORD / USER-AGENT） | 必须排在 AdBlock **之前**，否则 `HOST-SUFFIX,l.qq.com,REJECT` 这类宽泛拦截会抢先把 `fairplay.l.qq.com` 等直连域名拦掉 |
| 2 | `AdBlock.list` | 去广告与劫持拦截，统一 `REJECT` | 排在具体直连之后，只拦截没有被直连规则命中的域名 |
| 3 | `DirectGeo.list` | 兜底直连：`10.0.0.0/8` 等内网网段、`IP-ASN,132203`、`GEOIP,cn` | 必须排在 AdBlock **之后**，否则 `geoip,cn` 会把国内广告域名也一并放行 |

> 只导入 `Direct.list` 和 `AdBlock.list`、漏掉 `DirectGeo.list` 的后果是：没有被任何规则命中的国内流量不再兜底直连，会走默认策略。**三份都要加。**

### 2. 重写（`[rewrite_remote]`）—— 一份

```ini
[rewrite_remote]
https://raw.githubusercontent.com/MikeHuang01/MikeHuang01-Rules/main/QuantumultX/AdvertisingLite.conf, tag=AdvertisingLite, enabled=true
```

`AdvertisingLite.conf` **只能**加到「重写」，不要加到「分流」，否则会被当成一条规则解析失败。启用重写还必须在 QX 中开启 MITM 并信任证书，文件末尾的 `hostname = ...`（912 个主机）就是 MITM 域名列表。

### 3. 分流与重写的分工

| 层 | 文件 | 匹配对象 | 动作 |
| --- | --- | --- | --- |
| 直连 | `Direct.list` | 请求域名 | `direct` |
| 去广告 | `AdBlock.list` | 请求域名 / IP 网段 | `REJECT` |
| 兜底直连 | `DirectGeo.list` | IP 网段 / ASN / 国家 | `direct` |
| 重写 | `AdvertisingLite.conf` | 完整 URL（正则） | `reject` / `reject-200` / `reject-dict` / 响应脚本 |

域名类广告用「去广告」层拦截；已经拿到具体接口、但返回体里混着正常内容的，用「重写」层的 `reject-dict` 或响应脚本处理；两者不要重复写同一条。

## 三、Shadowrocket 导入

在「配置 → 模块 / 规则」中添加远程规则集，顺序同样是 Direct → AdBlock → DirectGeo：

| 用途 | 远程规则地址 |
| --- | --- |
| 直连 | `https://raw.githubusercontent.com/MikeHuang01/MikeHuang01-Rules/main/Shadowrocket/Direct.conf` |
| 去广告 | `https://raw.githubusercontent.com/MikeHuang01/MikeHuang01-Rules/main/Shadowrocket/AdBlock.conf` |
| 兜底直连 | `https://raw.githubusercontent.com/MikeHuang01/MikeHuang01-Rules/main/Shadowrocket/DirectGeo.conf` |

Shadowrocket 侧把 `HOST` 转成 `DOMAIN`、`HOST-SUFFIX` 转成 `DOMAIN-SUFFIX`、`HOST-KEYWORD` 转成 `DOMAIN-KEYWORD`，IP 网段统一附加 `no-resolve`，策略名统一大写 `DIRECT` / `REJECT`。

## 四、添加自己的规则

**只改 `QuantumultX/CustomDirect.list`**，在文件末尾追加。`Direct.list`、`AdBlock.list` 等自动生成的文件会在下次同步时被覆盖。

`CustomDirect.list` 目前包含这些自定义直连（同步时始终优先保留）：

```text
# > 容易忽视的直连分流
host, sdkapp.uve.weibo.com, direct
host, akkcloud.org, direct
host, psac3.aoppsac.com, direct
host, go.toter.me, direct

# > 本地网络与国内直连
ip-cidr, 10.0.0.0/8, direct
ip-cidr, 127.0.0.0/8, direct
ip-cidr, 172.16.0.0/12, direct
ip-cidr, 192.168.0.0/16, direct
ip-cidr, 224.0.0.0/24, direct
ip-cidr, 182.254.116.0/24, direct
IP-ASN,132203,Direct
host, wanwanzhou.top, direct
geoip, cn, direct
```

常见写法：

```text
HOST,example.com,direct                  精确域名
HOST-SUFFIX,example.com,direct          含所有子域名
HOST-KEYWORD,example,direct             域名中含该字符串
IP-CIDR,192.0.2.0/24,direct,no-resolve  网段直连
```

脚本会按规则类型自动分流：`HOST` / `HOST-SUFFIX` / `HOST-KEYWORD` / `USER-AGENT` / `URL-REGEX` 写进 `Direct.list`，`IP-CIDR` / `IP6-CIDR` / `IP-ASN` / `GEOIP` 写进 `DirectGeo.list`，你不必关心该加到哪一份。策略名大小写会统一成 `direct`。

去重键是「规则类型 + 匹配值」（不区分大小写）：`HOST,ad.12306.cn,DIRECT` 与 `host, ad.12306.cn, direct` 视为同一条，自定义规则优先保留。

## 五、自动同步

上游来源：

- [blackmatrix7 Direct.list](https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/master/rule/QuantumultX/Direct/Direct.list)
- [blackmatrix7 Advertising.list](https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/master/rule/QuantumultX/Advertising/Advertising.list)
- [blackmatrix7 Hijacking.list](https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/master/rule/QuantumultX/Hijacking/Hijacking.list)
- [blackmatrix7 AdvertisingLite.conf](https://cdn.jsdelivr.net/gh/blackmatrix7/ios_rule_script@master/rewrite/QuantumultX/AdvertisingLite/AdvertisingLite.conf)（重写）

[规则同步 Action](https://github.com/MikeHuang01/MikeHuang01-Rules/actions/workflows/sync-direct.yml) 每 6 小时执行一次：

1. `sync-direct.py`：合并上游 Direct 与自定义规则，拆成 `Direct.list` + `DirectGeo.list`，并生成 Shadowrocket 版本；
2. `sync-adblock.py`：合并上游 Advertising + Hijacking，统一 `REJECT`，生成 `AdBlock.list` 与 Shadowrocket 版本；
3. `sync-advertising-lite.py`：重新下载上游 `AdvertisingLite.conf`，补回支付宝/菜鸟 3 条明确广告 API 规则、12306 与菜鸟 2 条抓包确认的广告响应规则、哈啰与掌上公交 2 条响应脚本规则及所需 MITM 主机；
4. `check-rules.py`：校验规则类型、字段、重复项和分层契约，**校验不通过就不提交**；
5. 只有生成内容确实变化时才自动提交。

GitHub 定时任务可能有几分钟到更长时间的执行延迟。需要立即同步时，打开上面的链接，点击 **Run workflow**，选择 **main** 分支运行。

### 本地复现

```bash
pip install --upgrade pip            # 仅需标准库，无需第三方包
python3 scripts/sync-direct.py
python3 scripts/sync-adblock.py
python3 scripts/sync-advertising-lite.py
python3 scripts/check-rules.py
```

网络不稳时可以把上游文件先下载到一个目录，再用 `RULES_UPSTREAM_CACHE` 复用（按文件名匹配，脚本不会重复下载）：

```bash
RULES_UPSTREAM_CACHE=./upstream-cache python3 scripts/sync-adblock.py
```

## 六、为什么这样分层

历史上 `Direct.list` 与 `AdBlock.list` 都放在「分流」里，容易出现的两个问题是：

1. **宽泛拦截吃掉直连**：AdBlock 里的 `HOST-SUFFIX,l.qq.com,REJECT`、`HOST-KEYWORD,umeng,REJECT` 会命中 Direct 里写的 `fairplay.l.qq.com`、`msg.umeng.com` 等具体直连域名。QX 按顺序匹配，先命中的生效，所以这些直连规则其实从未生效（当前共有 **24 条**处于这种状态）。把 `Direct.list` 放到 `AdBlock.list` 之前即修复，`sync-adblock.py` 每次都会打印这 24 条，便于复核。
2. **`geoip,cn` 放错位置**：如果 `geoip,cn,direct` 排在 AdBlock 之前，国内广告域名会全部直连放行，去广告形同虚设。因此把它单独拆到 `DirectGeo.list`，排在 AdBlock 之后。

## 七、广告规则说明

去广告规则来自 blackmatrix7 的 Advertising 与 Hijacking 列表。Hijacking 中与 Advertising 重复的条目会被跳过，最终都转换为 `REJECT` 便于排查误拦截。

`QuantumultX/AdvertisingLite.conf` 由仓库的每 6 小时同步任务从 blackmatrix7 上游重新生成，并自动合并 3 条支付宝内菜鸟小程序广告 API 规则、12306 配置接口和菜鸟已抓包的广告记录接口响应规则，以及哈啰与掌上公交的响应脚本规则。脚本见 [`QuantumultX/targeted-ad-response.js`](QuantumultX/targeted-ad-response.js)：12306 只关闭 `data.ads_banner_conf[].conf[]` 中明确为 `isShow=true` 的 banner；菜鸟只清空已识别的 `materialId` + `materialContentMapper`/`adUtArgs` 广告记录数组；哈啰只清空 `api.hellobike.com/api` 响应中带 `creative` 的 `data.adm` 广告记录；掌上公交只识别抓包确认的广告配置响应，关闭 `indexAd`、`lineAd`、`bannerAd`、`ztAdCover` 等布尔开关并清空广告专属字段。路线/站点等其他 JSON 响应、菜鸟非广告数组和未识别接口均原样放行；值为 `10` 的 `interstitialAd` 因语义不明而保留。

本次抓包没有出现哈啰开屏广告请求，哈啰规则不作扩展。实时公交抓包中仅 CMD=115 命中广告配置 envelope；广告短暂闪现尚无法归因，`interstitialAd=10` 的含义未确认因此保留，当前改写仅处理已识别配置中的明确广告字段，不宣称已解决短闪。若要继续定位，需在广告实际显示时重新抓包。支付宝出行也只有 SDK 模板和不透明的网关记录，没有可安全定位的广告内容接口，因此暂不加规则。上游另有一条被标注为“匿名选择”的 `researchservice.consultmerge` 规则，本仓库暂不启用，待确认其确属广告接口后再考虑添加。菜鸟 mini-program 的 `*.taobao.com` 接口规则按上游原样匹配；上游针对 `*.cainiao.com` 的原生菜鸟 App 规则才带 `_home` 排除条件，不能把该例外套用到小程序规则。此资源不等同于“屏蔽支付宝所有广告”，也不覆盖未验证的广告接口，避免误拦登录、支付或小程序核心接口。

铁路 12306 相关的 `ad.12306.cn` 与 `12306media.com` 已存在于 `QuantumultX/AdBlock.list`。blackmatrix7 上游 Direct 也包含精确主机 `ad.12306.cn`；为避免该广告主机绕过 `REJECT`，`sync-direct.py` 会从自定义与上游输入中排除这条直连规则。

## 八、故障排查

| 现象 | 先查这里 |
| --- | --- |
| 资源显示 0 条 / 更新失败 | `raw.githubusercontent.com` 是否可直连；国内网络常需代理或换 jsDelivr 镜像 |
| 去广告没生效 | 三份分流资源是否都在、顺序是否 Direct → AdBlock → DirectGeo |
| 某个 App 功能被误拦 | 在该 App 域名上抓到具体主机名后写入 `CustomDirect.list`，脚本会保证它优先于 AdBlock |
| 重写没生效 | 是否加到 `[rewrite_remote]`、MITM 是否开启并信任证书 |
| 支付宝/菜鸟广告 | 只覆盖已抓包确认的接口，未确认的接口不会被误拦 |

## 九、来源与维护

上游规则：[blackmatrix7/ios_rule_script](https://github.com/blackmatrix7/ios_rule_script)。上游的版权与许可归原作者所有；本项目只做整合、去重和客户端格式转换，并保留作者与仓库信息。

维护者：MikeHuang01。
