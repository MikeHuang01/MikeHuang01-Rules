# Clash / mihomo 规则集

本目录由 `scripts/sync-clash.py` 自动生成，**不要手改**。源头是 `QuantumultX/` 下的三份分流资源，因此 Clash 与 QX 永远是同一套规则，只是语法不同。

| 文件 | 来源 | 对应 QX 资源 | 条数 |
| --- | --- | --- | --- |
| `Clash/Direct.yaml` | `QuantumultX/Direct.list` | 具体域名直连（第 1 层） | 235 |
| `Clash/AdBlock.yaml` | `QuantumultX/AdBlock.list` | 去广告 / 劫持拦截（第 2 层） | 291,164 |
| `Clash/DirectGeo.yaml` | `QuantumultX/DirectGeo.list` | 兜底直连（第 3 层） | 7 |

条数以文件内 `# TOTAL:` 为准，这里只是量级参考。

## 一、和 QX / Shadowrocket 最关键的三个不同

### 1. 规则集里没有「策略」这一列

QX 与 Shadowrocket 的规则自带动作（`host, a.com, direct`、`DOMAIN,a.com,REJECT`）。Clash 的 rule-provider **只提供匹配条件**，动作写在引用它的那一行：

```yaml
rules:
  - RULE-SET,direct,🎯 直连      # 动作在这里
  - RULE-SET,adblock,🛑 广告拦截  # 也是在这里
```

所以三个文件里全是 `type,value`，没有第三列。想把去广告整体放行，不需要改规则文件，把 `🛑 广告拦截` 这个策略组切到 `DIRECT` 即可 —— 这是 Clash 侧比 QX 方便的地方。

### 2. 顺序由配置决定，而不是由导入顺序决定

QX 按 `[filter_remote]` 的导入顺序匹配，Clash 按 `rules:` 里 `RULE-SET` 出现的先后匹配。契约完全一样，只是控制点从「资源列表」变成了「规则列表」：

```yaml
rules:
  - RULE-SET,direct,🎯 直连        # 第 1 层：具体直连，必须最前
  - RULE-SET,adblock,🛑 广告拦截    # 第 2 层：去广告
  - RULE-SET,directgeo,🎯 直连      # 第 3 层：兜底直连，必须在去广告之后
```

把 `directgeo`（含 `GEOIP,CN`）排到 `adblock` 之前，国内广告域名会被整体放行，去广告立刻失效 —— 与 QX 里把 `geoip,cn` 提到 AdBlock 前面是同一个错误。

### 3. 去广告只剩「域名级拦截」，没有 MITM 重写

QX 的 `[rewrite_remote]`（`QuantumultX/AdvertisingLite.conf`，1242 条 rewrite + 910 个 MITM 主机）依赖 MITM 解密与 JS 注入。**mihomo 没有 MITM 与脚本能力，这部分无法迁移**，本目录也不会生成对应文件。

| QX 能力 | Clash 是否支持 | 说明 |
| --- | --- | --- |
| `[filter_remote]` 三份分流 | ✅ 完全对应 | 即本目录三个 YAML |
| `[rewrite_remote]` URL 重写 | ❌ | 无 MITM；只能在域名层 REJECT |
| 响应脚本 / `reject-dict` / JSON 改写 | ❌ | 同上 |
| `USER-AGENT` 规则 | ❌ | mihomo v1.19 起已移除该规则类型，生成时自动跳过 |
| `IP-ASN` 规则 | ✅ 需 `ASN.mmdb` | 放错目录会尝试联网下载并导致启动失败 |
| `GEOIP` 规则 | ✅ 需 `geoip.dat` / `Country.mmdb` | 与 QX 的 `geoip,cn` 等价 |

结论：**Clash 侧的去广告覆盖面等于 QX 的分流层，不等于 QX 的重写层。** 靠 `reject-dict` 才能清干净的接口型广告（返回体里混着正常内容），在 Clash 里无法处理。

## 二、配置写法

```yaml
rule-providers:
  direct:
    type: http
    behavior: classical
    url: "https://cdn.jsdelivr.net/gh/MikeHuang01/MikeHuang01-Rules@main/Clash/Direct.yaml"
    path: ./ruleset/direct.yaml
    interval: 86400

  adblock:
    type: http
    behavior: classical
    url: "https://cdn.jsdelivr.net/gh/MikeHuang01/MikeHuang01-Rules@main/Clash/AdBlock.yaml"
    path: ./ruleset/adblock.yaml
    interval: 86400

  directgeo:
    type: http
    behavior: classical
    url: "https://cdn.jsdelivr.net/gh/MikeHuang01/MikeHuang01-Rules@main/Clash/DirectGeo.yaml"
    path: ./ruleset/directgeo.yaml
    interval: 86400
```

```yaml
rules:
  - RULE-SET,direct,🎯 直连
  - RULE-SET,adblock,🛑 广告拦截
  - RULE-SET,directgeo,🎯 直连
  - MATCH,🚀 节点选择
```

## 三、注意事项

1. **`behavior` 必须是 `classical`。** 三份文件里都含 `IP-CIDR` / `IP-ASN` / `GEOIP` 这类非域名规则，写成 `behavior: domain` 会解析失败或静默丢规则。
2. **`Clash/AdBlock.yaml` 有 29 万条**，约 11 MB。建议 `interval: 86400`，不要设成 3600。
3. **`IP-ASN,132203` 需要 `ASN.mmdb`。** 放在 mihomo 的工作目录（`-d` 指向的目录）里；缺失时 mihomo 会尝试从 GitHub 下载，国内网络下这一步会失败并让整份配置加载失败。
4. **raw.githubusercontent.com 在国内经常不通**，上例统一用 jsDelivr 镜像；裸 raw 地址只适合能直连的环境。
5. **不要同时挂载 QX 的 `.list` 和本目录的 `.yaml`。** 语法不同（`HOST` vs `DOMAIN`），Clash 解析 QX 语法会报 `unsupported rule type`。
6. **Clash Verge Rev 的本地配置请直接引用本目录的三个 YAML**，不要再从 blackmatrix7 的 `Clash/` 目录另取一份，否则会出现两份真相，顺序与内容都可能漂移。
7. 规则**首次匹配即生效**，兜底 `MATCH` 必须最后一行，否则它后面的规则永远不执行。

## 四、校验

```bash
python scripts/sync-clash.py     # 重新生成
python scripts/check-rules.py    # 校验：类型合法、无重复、无被遮蔽规则、层间契约
```

`check-rules.py` 会同时校验 QX / Shadowrocket / Clash 三套产物，任一格式出现重复或非法类型都会让它以非零码退出。
