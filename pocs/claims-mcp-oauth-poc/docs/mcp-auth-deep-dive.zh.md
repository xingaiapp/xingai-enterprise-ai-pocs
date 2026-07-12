# MCP 认证深度讲解——用这个 POC 的代码当例题

**English:** [mcp-auth-deep-dive.md](./mcp-auth-deep-dive.md)

写这篇文档的原因是：在架构图里读到"OAuth 2.1 + PKCE",和能讲清楚"每一块为什么存在、少了它会出什么问题",是两个完全不同层次的理解。下面每一节都指向这个 POC 里真实的代码(`auth_server/`、`mcp_server/`、`client/`),让你可以对着代码读讲解——而且是在保险理赔裁定这个领域,搞错了会有真实的财务和监管后果,不只是一个 demo 翻车。

---

## MCP 认证要解决的三方问题

任何一个 MCP 部署里都有三方,彼此的信任程度不一样：

| 角色 | 本例中对应 | 应该能证明/做到什么 |
|------|-----------|---------------------|
| **资源所有者** | 保险公司——拥有理赔数据 | 授予或拒绝访问；定义"允许"的含义 |
| **客户端 / Agent** | 理赔顾问辅助 Agent（`client/`） | 证明自己拿到了有效授权，同时永远不持有资源所有者的主账户凭证 |
| **资源服务器** | 理赔 MCP 服务器（`mcp_server/`） | 校验一个凭证，不需要信任客户端自己说的话 |

核心问题是：Agent 怎么证明自己有权限读 `CLM-8841`、并且（权限更窄地）裁定它，**同时保险公司的登录凭证从来不会被输入到、存储在、或经过 Agent**？这就是为什么要用 OAuth，而不是"让 Agent 直接用用户名密码登录"的全部原因。

### 不这么做会出什么问题

设想一下 `client/main.py` 直接在配置文件里存了理赔系统的用户名密码（这是真实社区版 MCP 服务器出现过的模式——这个 POC 背后的原始文章专门点名过 Robinhood 的这个案例）。具体来说,这个配置文件一旦泄露：

- 拿到它的人可以**以理赔顾问的身份**登录理赔系统,拥有顾问的*全部*权限——不是 Agent 实际需要的 `claims.read`/`claims.review` 那一小片。
- 没法只撤销*Agent 的*访问权限而不改顾问的真实密码——改了顾问自己也登不进去了。
- 没有 token 过期这回事——这个凭证一直有效，直到有人发现并轮换它。

OAuth 的全部价值主张就是把"偷一个配置文件 = 拿到某人的真实登录"变成"偷一个配置文件 = 拿到一个权限窄、生命周期短、可单独撤销的 token,做不了 scope 之外的任何事，而且不到 5 分钟就失效"。见 `client/token_store.py`——就连*token 本身*存储时都是 `chmod 600`，而且它依然不是凭证；它是一个窄范围、有时限的证明。

---

## PKCE——人人挂在嘴边，很少有人能推导出来

PKCE(Proof Key for Code Exchange，RFC 7636)在 OAuth 2.1 里不是可选的装饰——它是强制的，理解为什么需要走一遍它堵住的那个攻击。

### PKCE 防的是什么攻击

没有 PKCE 时，授权码流程是：客户端把浏览器重定向到授权服务器，人登录并同意，授权服务器把浏览器重定向回客户端的 `redirect_uri` 并带上一个短生命周期的 `code`，客户端拿这个 `code` 去换 token。

漏洞在于：这个 `code` 会经过浏览器，出现在浏览器历史里，可能通过 referrer 头泄露，而且——对原生/桌面应用来说尤其关键——**同一台机器上的恶意应用**有可能拦截这次重定向（比如注册了同一个自定义 URL scheme，或者利用共享/配置错误的 loopback 端口）,在合法客户端看到之前偷走这个 `code`。谁拿到了 code，谁就能去兑换 token。

### 具体是怎么修的

```python
# client/oauth.py — generate_pkce_pair()
verifier = base64.urlsafe_b64encode(os.urandom(32)).rstrip(b"=").decode("ascii")
digest = hashlib.sha256(verifier.encode("ascii")).digest()
challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
```

1. 客户端生成一个随机密钥，`code_verifier`（43个字符以上，暂时哪都不发）。
2. 派生出 `code_challenge = BASE64URL(SHA256(code_verifier))`，在最初的 `/authorize` 重定向里**只发这个 challenge**。
3. 拿 code 换 token 时，客户端发的是 **verifier**（不是 challenge）给 `/token`。
4. 授权服务器独立计算 `SHA256(verifier)`，检查它是否匹配签发这个 code 时存下来的 `challenge`：

```python
# auth_server/security.py — verify_pkce()
digest = hashlib.sha256(code_verifier.encode("ascii")).digest()
expected = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
return hmac.compare_digest(expected, code_challenge)
```

**为什么这就堵住了攻击：** 一个从重定向里偷到 `code` 的攻击者依然没有 `verifier`——它从来没离开过合法客户端的进程，从来没出现在任何 URL 里，从来没碰过浏览器。没有 verifier，偷来的 code 在 token 端点那里毫无用处。这是一个单向哈希关系：知道 challenge 推不出 verifier（这正是 SHA-256 买来的东西）。

**手算例子，想自己验证的话：**

```python
>>> import base64, hashlib
>>> verifier = "dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk"
>>> digest = hashlib.sha256(verifier.encode("ascii")).digest()
>>> base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
'E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM'
```

自己跑一遍——这正是 `verify_pkce()` 跑的那两行，也是为什么 `tests/test_auth_server.py::TestPKCE::test_pkce_tampered_challenge`（把 challenge 改一个字符，校验就失败）是一个真正有意义的测试，不是走个形式。

**还有一个值得注意的细节：** `verify_pkce` 用的是 `hmac.compare_digest`，不是 `==`。朴素的字符串比较会在第一个不匹配的字节处短路，"第 3 个字节就错了"和"第 40 个字节才错"之间那一点点时间差——试的次数够多的话——是攻击者可以用来逐字节猜出 challenge 的真实侧信道。这是个很慢的攻击，但既然常数时间比较不花什么代价，就没理由留这扇门开着。

---

## `state` 参数——防的是 CSRF，不是 PKCE 的活

PKCE 和 `state` 解决的是**不同**的问题，两个都需要：

- **PKCE** 证明发起授权请求的客户端和兑换 code 的客户端是同一个（保护 code 兑换环节）。
- **`state`** 证明客户端正在处理的授权响应，对应的是*它自己*发起的那次请求（防伪造回调）。

没有 `state` 的话，攻击者可以诱骗受害者的浏览器去完成*攻击者自己的* OAuth 流程，让攻击者的授权码落进受害者的回调里——一种类似会话固定的 CSRF 攻击。`client/main.py` 生成一个随机 `state`，在 `/authorize` 重定向里发出去，如果回调返回的 `state` 对不上就拒绝：

```python
if callback.get("state") != state:
    raise ValueError("state mismatch — possible CSRF attack!")
```

这个检查必须在 code 被拿去兑换 token **之前**发生——state 不匹配是硬停止，不是警告。

---

## 为什么"发现"机制对 MCP 特别重要

`.well-known/oauth-authorization-server`（RFC 8414）和 `.well-known/oauth-protected-resource/mcp`（RFC 9728）让 `client/discovery.py` 通过两次 HTTP 调用就学到所有端点 URL——`authorization_endpoint`、`token_endpoint`、`jwks_uri`——而不是每个部署都硬编码一套配置。

这对 MCP 来说不是可有可无的加分项：**MCP 的整个卖点就是一个客户端要跟很多个独立运营的服务器打交道。** 如果理赔顾问辅助 Agent 得把 A 保险公司的认证端点硬编码进去，换成 B、C、D 公司就得重写 N 份配置。发现机制意味着客户端的*代码*从不改变——把它指向另一个理赔 MCP 服务器，它就会从那个服务器自己公布的元数据里启动自己的认证流程。

`client/discovery.py` 还强制了另一件值得注意的事：如果发现的授权服务器在 `code_challenge_methods_supported` 里没有声明支持 `S256`，它会拒绝继续：

```python
if "S256" not in pkce_methods:
    raise ValueError("AS does not support S256 PKCE — refusing to connect")
```

一个理赔 Agent 不应该仅仅因为它发现的某个服务器碰巧支持更弱的方式（或者压根不支持）就自降安全等级。拒绝并大声报错，不要悄悄将就。

---

## 短生命周期、绑定 audience 的 JWT——防的是爆炸半径，不只是"签过名"

`auth_server/security.py` 的 `create_access_token` 用 RS256（非对称——MCP 服务器只需要*公钥*就能校验，就算完全被攻破也永远无法伪造 token）签发 JWT，并设置：

```python
"iss": ISSUER,       # 谁签发的
"aud": audience,      # 这个 token 是给谁用的——见下文
"exp": now + ttl,     # 默认 5 分钟
"scope": scope,       # 授权了什么
```

两个属性承担了大部分安全工作：

1. **短 TTL（5分钟）。** 偷来的 token 只在几分钟内有用，不是永久有效。`client/token_store.py` 的 `get_valid_access_token()` 会在过期前主动刷新，所以这个代价对正常使用是无感的，但对攻击者是真实的。
2. **Audience 绑定。** `aud` 指名*这个具体的理赔 MCP 服务器*。如果同一套 OAuth 模式被部署给第二个不相关的资源（比如一个保单报价 MCP 服务器），一个为理赔服务器铸造的 token 在那边校验会失败——`jwt.InvalidAudienceError`——就算它是一个完全有效、未过期、签名正确的 token。这就防止了一个从某个系统泄露的 token，仅仅因为共用同一个授权服务器，就能被重放到另一个不相关的系统上。

---

## 四层防护模型

这是把整套系统一次性装进脑子里的心智模型——四道独立的检查，各自回答不同的问题，谁都替代不了谁：

```text
第 1 层 — 身份            "你是谁？"
  OAuth 2.1 + PKCE          mcp_server/auth.py: verify_token()
  防的是：伪造/偷来的凭证、授权码拦截

第 2 层 — API 授权         "你能调哪些工具？"
  Scope + Audience          mcp_server/auth.py: require_scopes()
  防的是：一个只有 claims.read 的授权被用来调 claims.adjudicate

第 3 层 — Agent 授权       "你能做多大的事？"
  Agent 策略（墙 #2）        mcp_server/policies.py: check_adjudication_policy()
  防的是：一个有效的 claims.adjudicate token 裁定一笔超出本 Agent 理赔权限、
  超出理赔类型白名单、或者不在 AI 辅助队列里的理赔

第 4 层 — 业务确认         "这笔是不是走对了流程？"
  Review → Adjudicate + 幂等性   mcp_server/tools.py
  防的是：一个决策没有先冻结、（真实部署里）没有人工确认就生效；
  网络重试导致重复裁定
```

**最关键的洞察，尽量说得直白一点：授权一个 Agent 能访问理赔系统，跟授权它能把技术上能调用 API 做到的每一笔结算都真正落地，根本不是一回事。** 一份写着"OAuth 配置得没问题"的事故报告，跟写着"什么都没出错"的事故报告，不是同一回事——第 3 层和第 4 层才是一个理赔顾问辅助 Agent 里大部分真实业务风险所在的地方，而这恰恰是一篇泛泛而谈"接了 OAuth"的企业 MCP 文章通常会跳过的部分。

---

## Scope 不是策略（双墙模型细讲）

很容易把 `claims.adjudicate` 读成"这个 Agent 能裁定理赔"然后就此打住。`mcp_server/policies.py` 存在的目的就是打破这个假设：

```python
def check_adjudication_policy(claim: dict, settlement_amount: float) -> None:
    if claim["status"] != AI_ASSIST_QUEUE_STATUS:
        raise HTTPException(403, "... not in the AI-assist queue ...")
    if claim["claim_type"] not in ALLOWED_CLAIM_TYPES:
        raise HTTPException(403, "... outside agent settlement authority ...")
    if settlement_amount > MAX_SETTLEMENT_USD:
        raise HTTPException(403, "... exceeds agent settlement authority ...")
```

这里的每一项检查都是在 OAuth scope 检查**已经通过之后**才跑的。一个持有完全有效、未过期、scope 正确、真实认证过的顾问会话 token 的调用者，如果这一笔具体理赔超出边界，在这里照样会被拒绝，返回 403。这是刻意的纵深防御，而且它对应着一个真实存在、早于本 POC 的保险行业概念：**理赔权限分级**。一个真实保险公司的初级理赔顾问，不会因为登录成功了就能裁定一笔六位数的理赔——他们的*权限等级*限定了不升级审批就能批准的范围，跟他们的登录是否有效完全无关。这个 POC 把它的 Agent 建模成团队里最初级的顾问：理赔类型窄、金额上限低，还进一步限定在一个由 ops 负责人明确路由过来做 AI 辅助处理的、被隔离出来的理赔子集里（`AI_ASSIST_QUEUE_STATUS`）——对应 Robinhood 那个隔离的、单独入金的 Agentic 账户在理赔领域的等价物，本 POC 所借鉴的真实系统正是出于同样的原因用了这个设计（见 `xingai-robinhood-mcp` ADR-001 的 G6 门）。

---

## Review → Adjudicate 是跟 OAuth 独立的另一道防线

`review_claim_decision` 和 `submit_claim_decision` 是两个不同的工具、需要两个不同的 scope，理由跟 OAuth 的机制本身无关：**一个仅仅是提议的决策，和一个已经生效的决策，风险等级不一样，把它们合并成一次工具调用，就失去了分别给它们设门禁的能力。**

```python
# mcp_server/tools.py — tool_submit_claim_decision()
def tool_submit_claim_decision(review_id: str, idempotency_key: str, user_id: str) -> dict:
    ...
```

注意这个函数签名**没有**接受什么：`claim_id`、`decision`、`settlement_amount`。所有重要的东西在 `review_claim_decision` 跑的那一刻就已经冻结进 review 记录里了。没有任何代码路径——不是参数，不是请求头，什么都不是——能让 `submit_claim_decision` 这次调用去让一个没有被原样 review 过的决策生效。如果一个 Agent（或者它背后一个困惑/被操纵的 LLM）试图在 submit 时"贴心地"调整结算金额，压根没有字段可以放这个调整。它必须重新走一遍 `review_claim_decision`，而这会从头重新跑一遍墙 #2。

在真实部署里，review 和 submit 之间的这段空隙正是人工顾问确认应该发生的地方（`client/main.py` 的 `input("Type YES to finalize...")` 就是这个环节的 demo 替身）。OAuth 在几分钟或几小时前 token 签发的那一刻，回答的是"这个 Agent 是否被允许接触理赔系统"——它回答不了"人类是否同意这个具体的 $640 决策，就在此刻"。这是一个在不同时间问的不同问题，需要一个不同的机制。

---

## 幂等性是安全属性，不只是体验优化

```python
with _idempotency_lock:
    cached = _idempotency_results.get(idempotency_key)
    if cached:
        return {**cached, "idempotent": True}
```

网络调用会失败、超时、被重试——可能是 Agent 自己的重试逻辑，也可能是人重新点了一下。没有幂等性 key 的话，一次重试的 `submit_claim_decision` 调用会试图把同一个 `review_id` 兑现两次；`review["used"]` 已经用 409 挡掉了这个具体情况。但幂等性 key 保护的是一个相关但更隐蔽的情况：响应在传输过程中丢了，但第一次调用其实在服务端已经成功了——客户端分不清"失败了"和"成功了但我没收到响应"，这时候如果盲目地用一个*新*的 `idempotency_key`（或者不带）去重试，就有二次生效的风险。把缓存结果的 key 定成客户端提供的 `idempotency_key`，能让重试可证明地安全：同样的 key，不管发多少次，结果永远一样。

---

## 从这个 POC 到真实的理赔部署

| 本 POC | 生产环境对应 |
|--------|--------------|
| `auth_server/`（内存存储，一个硬编码用户） | Okta / Auth0 / Azure AD B2C，或一套加固过的自建 IdP，带真实登录、MFA、会话管理 |
| `mcp_server/policies.py` 的 `MOCK_CLAIMS`/`MOCK_POLICIES` | 真实的 MCP 封装层，接在 Guidewire ClaimCenter、Duck Creek Claims 或自建理赔系统前面 |
| `MAX_SETTLEMENT_USD` / `ALLOWED_CLAIM_TYPES`（两个常量） | 一套真实的权限矩阵服务，每个 Agent 部署/分支机构一份配置，有版本、可审计 |
| 内存里的 `_reviews` / `_idempotency_results` / `storage` dict | PostgreSQL（code、client、同意记录）+ Redis（短 TTL 的 code、幂等性 key），在多副本之间共享 |
| 磁盘上的 `keys/private.pem` | Key Vault / HSM；支持重叠有效期的 JWKS 密钥轮换 |
| 没有审计轨迹 | Append-only 日志（谁、哪笔理赔、什么工具、什么决策、什么结果），按各州保险监管要求留存 |
| 固定的 demo 同意，不持久化 | 真实的、可查询、可撤销的（用户，client，scope）同意记录 |
| 没有限流 | 按 Agent、按工具的限流——等真正由 LLM（不是这个 POC 的脚本化演示）决定何时调工具时，这一点只会更重要 |
| 本地明文 HTTP | 全程 HTTPS；token 端点响应标记 no-store |

## 上线前检查清单

改编自[原始实验课](https://github.com/xingaiapp/xingai-enterprise-ai-design/blob/main/guides/2026-07-12-mcp-oauth-pkce-lab.zh.md)的生产升级检查清单——下面每一项没打勾的，在真正碰理赔系统之前都当成真实的阻塞项，不是"最好有"：

**授权服务器**
- [ ] 授权码单次使用，TTL ≤ 120秒，强制 `code_challenge_method=S256`（绝不允许 `plain`）
- [ ] PKCE 校验用常数时间比较
- [ ] `redirect_uri` 精确字符串匹配，绝不前缀/通配符匹配
- [ ] Access token TTL ≤ 300秒；refresh token 轮换时旧 token 在新 token 签发那一刻立即失效
- [ ] 吊销端点对未知 token 也返回 200（防止枚举探测）
- [ ] 绝不给客户端返回空的 `access_token`（见下面"值得单独点名的常见错误"）
- [ ] 私钥存在 Key Vault/HSM 里，绝不在仓库里或通用文件系统上
- [ ] 同意记录持久化、可查询、可从管理后台撤销

**理赔 MCP 服务器**
- [ ] 每次请求都校验——不跨请求缓存"这个 token 有效"的结果
- [ ] `iss`、`aud`、`exp` 全部检查，不只是签名
- [ ] 每个工具有自己独立的 scope 要求；权限不足返回 403，不是 401
- [ ] Agent 策略（墙 #2）独立于 scope 实现，绝不并入 scope 检查
- [ ] Review 记录存在真实数据库里，带行级锁，不是进程内 dict
- [ ] Submit/adjudicate 从不接受可变业务参数——只接受一个 review 引用
- [ ] 幂等性 key 有明确的保留期限（比如7天），不是永久
- [ ] 错误响应从不泄露内部堆栈跟踪
- [ ] 按 Agent、按工具都有限流

## 值得单独点名的常见错误

这个 POC 背后的原始文章提到过一个真实的、社区版 Robinhood MCP 客户端里报告过的失败模式：一个 token 端点返回 HTTP 200，但 `access_token` 是**空的**，却被悄悄当成登录成功处理了。`client/oauth.py` 的 `exchange_code_for_token` 专门防了这个：

```python
access_token = token_data.get("access_token", "")
if not access_token:
    raise ValueError("Token response contains no access_token — refusing to treat this as a successful login")
```

这个具体 bug 背后的一般性教训是：**选对协议（OAuth 2.1 + PKCE）是必要条件，不是充分条件。** 每一次 token 兑换、每一次凭证校验、外部系统的每一个响应，都需要自己明确的校验——"HTTP 调用返回了 200"是一个传输层的事实，不是一个业务层"确实发生了有用的事"的保证。
