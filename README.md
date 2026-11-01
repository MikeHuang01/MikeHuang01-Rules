# MikeHuang01 规则配置

面向 **QuantumultX** 与 **Shadowrocket** 的分流、直连和去广告规则集。Direct 规则会定时从上游实时抓取，再与你的自定义规则合并、去重，生成客户端可直接导入的文件。

## 快速导入

### QuantumultX

在 QuantumultX 的“设置 → 配置文件 → 分流”中添加远程资源：

| 用途 | 远程分流地址 |
| --- | --- |
| 直连（自动同步上游 + 你的自定义规则） | `https://raw.githubusercontent.com/MikeHuang01/MikeHuang01-Rules/main/QuantumultX/Direct.list` |
| 去广告与劫持拦截 | `https://raw.githubusercontent.com/MikeHuang01/MikeHuang01-Rules/main/QuantumultX/AdBlock.list` |

添加后将对应策略保持为文件中的 `Direct` / `REJECT`，并确认分流顺序符合自己的需要。中国大陆网络访问 `raw.githubusercontent.com` 不稳定时，可把域名替换为可用的 GitHub Raw 镜像，文件路径保持不变。

### Shadowrocket

在 Shadowrocket 的“配置 → 模块 / 规则”中添加远程规则集：

| 用途 | 远程规则地址 |
| --- | --- |
| 直连（自动同步上游 + 你的自定义规则） | `https://raw.githubusercontent.com/MikeHuang01/MikeHuang01-Rules/main/Shadowrocket/Direct.conf` |
| 去广告与劫持拦截 | `https://raw.githubusercontent.com/MikeHuang01/MikeHuang01-Rules/main/Shadowrocket/AdBlock.conf` |

如果在客户端里手动选择策略，直连文件使用 `DIRECT`，拦截文件使用 `REJECT`。Shadowrocket 的规则集使用 `DOMAIN`、`DOMAIN-SUFFIX`、`DOMAIN-KEYWORD`，IP 网段附带 `no-resolve`。

## 当前规则

- `QuantumultX/Direct.list`：自动生成的 QX 分流文件，合并自定义与上游 Direct 规则。
- `QuantumultX/AdBlock.list`：291,165 条唯一规则，合并 Advertising 与 Hijacking，统一拦截。
- `QuantumultX/CustomDirect.list`：**只在这里维护你的自定义直连规则**，同步不会覆盖该文件。
- `Shadowrocket/Direct.conf`：从合并后的 Direct 规则转换生成，供 Shadowrocket 使用。
- `Shadowrocket/AdBlock.conf`：与 QX 广告规则一一对应。

每次生成都按“规则类型 + 匹配值”去重，且不区分大小写。例如 `HOST,ad.12306.cn,DIRECT` 与 `host, ad.12306.cn, direct` 视为同一条，只保留一条。

## 自动同步方式

上游来源：[blackmatrix7 Direct.list](https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/master/rule/QuantumultX/Direct/Direct.list)。

[规则同步 Action](https://github.com/MikeHuang01/MikeHuang01-Rules/actions/workflows/sync-direct.yml) 每 6 小时抓取一次上游：

1. 读取 `QuantumultX/CustomDirect.list`；
2. 实时下载上游 Direct 列表；
3. 合并两边的规则并去重；
4. 生成 QX 的 `QuantumultX/Direct.list`；
5. 同步生成 Shadowrocket 的 `Shadowrocket/Direct.conf`；
6. 只有内容确实变化时才自动提交。

GitHub 的定时任务可能有几分钟到更长时间的执行延迟。需要立即更新时，打开上面链接，点击 **Run workflow**，选择 **main** 分支并运行。

## 添加自己的规则

只修改 `QuantumultX/CustomDirect.list`，在文件末尾追加即可；不要把手工规则写进自动生成的 `Direct.list`，否则下一次同步会覆盖它。你的规则始终优先保留，上游出现同类型、同匹配值的重复项会自动跳过。

QuantumultX 常用格式：

```text
HOST,example.com,DIRECT
HOST-SUFFIX,example.com,DIRECT
HOST-KEYWORD,example,DIRECT
IP-CIDR,192.0.2.0/24,DIRECT,no-resolve
```

也可以在本地验证合并结果：

```bash
python3 scripts/sync-direct.py
```

需要在同一台机器上直接运行、又不想先等 Actions 时，执行脚本后会更新两份 Direct 文件；确认 Diff 正常再提交。

## 广告规则

去广告规则来自 blackmatrix7 的 Advertising 与 Hijacking 列表。Hijacking 中与 Advertising 重复的条目会被跳过，最终都转换为 `REJECT` 便于排查误拦截。

## 来源与维护

上游规则：[blackmatrix7/ios_rule_script](https://github.com/blackmatrix7/ios_rule_script)。上游的版权与许可归原作者所有；本项目只做整合、去重和客户端格式转换，并保留作者与仓库信息。

维护者：MikeHuang01。
