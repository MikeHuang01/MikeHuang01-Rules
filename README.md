# MikeHuang01 规则配置

面向 **QuantumultX** 与 **Shadowrocket** 的分流、直连和去广告规则集。配置按客户端分别维护，保留规则用途分区，并在整合时去掉重复项。

## 快速导入

### QuantumultX

在 QuantumultX 的“设置 → 配置文件 → 分流”中添加远程资源：

| 用途 | 远程分流地址 |
| --- | --- |
| 常用直连与补充规则 | `https://raw.githubusercontent.com/MikeHuang01/MikeHuang01-Rules/main/QuantumultX/Direct.list` |
| 去广告与劫持拦截 | `https://raw.githubusercontent.com/MikeHuang01/MikeHuang01-Rules/main/QuantumultX/AdBlock.list` |

添加后将对应策略保持为文件中的 `Direct` / `REJECT`，并确认分流顺序符合自己的需要。中国大陆网络访问 `raw.githubusercontent.com` 不稳定时，可把域名替换为可用的 GitHub Raw 镜像，文件路径保持不变。

### Shadowrocket

在 Shadowrocket 的“配置 → 模块 / 规则”中添加远程规则集：

| 用途 | 远程规则地址 |
| --- | --- |
| 常用直连与补充规则 | `https://raw.githubusercontent.com/MikeHuang01/MikeHuang01-Rules/main/Shadowrocket/Direct.conf` |
| 去广告与劫持拦截 | `https://raw.githubusercontent.com/MikeHuang01/MikeHuang01-Rules/main/Shadowrocket/AdBlock.conf` |

如果在客户端里手动选择策略，直连文件使用 `DIRECT`，拦截文件使用 `REJECT`。Shadowrocket 会把域名规则显示为 `DOMAIN`、`DOMAIN-SUFFIX`、`DOMAIN-KEYWORD`，IP 网段则附带 `no-resolve`。

## 当前规则

- `QuantumultX/Direct.list`：242 条唯一规则，含容易忽略的直连项、内网网段、国内解析和上游 Direct 列表。
- `QuantumultX/AdBlock.list`：291,165 条唯一规则，合并 Advertising 与 Hijacking 规则，统一为 `REJECT`。
- `Shadowrocket/Direct.conf`：与 QuantumultX 直连规则一一对应，完成客户端语法转换。
- `Shadowrocket/AdBlock.conf`：与 QuantumultX 广告规则一一对应，完成客户端语法转换。

每次合并都以“规则类型 + 匹配值”为键去重。例如 `HOST,ad.12306.cn,DIRECT` 与自定义的 `host, ad.12306.cn, direct` 视为重复，只保留一条。

## 规则结构

`Direct` 文件按以下顺序整理：

1. 自定义直连补充；
2. 本地网络与国内解析；
3. 上游 Direct 列表。

广告规则来自 blackmatrix7 的 Advertising 与 Hijacking 列表。Hijacking 中与 Advertising 重复的规则会被跳过，最终规则统一拦截，便于排查被错误拦截的域名。

## 添加自己的规则

可以直接在对应文件的分区末尾追加。QuantumultX 常用格式：

```text
HOST,example.com,DIRECT
HOST-SUFFIX,example.com,DIRECT
HOST-KEYWORD,example,DIRECT
IP-CIDR,192.0.2.0/24,DIRECT,no-resolve
```

Shadowrocket 常用格式：

```text
DOMAIN,example.com,DIRECT
DOMAIN-SUFFIX,example.com,DIRECT
DOMAIN-KEYWORD,example,DIRECT
IP-CIDR,192.0.2.0/24,DIRECT,no-resolve
```

修改后先确认规则值没有重复，再把客户端里的远程资源更新一次。若需要新增规则分类，建议在 `QuantumultX/` 与 `Shadowrocket/` 下建立同名文件，README 中同步登记用途和导入地址。

## 来源与维护

上游规则：[blackmatrix7/ios_rule_script](https://github.com/blackmatrix7/ios_rule_script)。上游的版权与许可归原作者所有；本项目只做整合、去重和客户端格式转换，并保留作者、仓库与上游更新时间字段。

维护者：MikeHuang01。后续新增或调整规则会继续同步到两套客户端目录。
