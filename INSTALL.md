# Installing AutoName

[English](#english) · [中文](#中文)

## English

Choose the entry that fits your workflow. Guided npx and Python entries run the same configuration wizard. Standard skill managers install the files, then the agent completes setup on first use.

| Entry | What it does | Configuration starts |
| --- | --- | --- |
| Guided `npx` | Runs the bundled installer without a permanent CLI installation. | Immediately. |
| Standard `npx skills add` | Installs AutoName into the selected agents. | When the skill is first invoked. |
| Global npm CLI | Installs a reusable `autoname` command. | When you run `autoname`. |
| Direct Python/source | Runs the installer from a downloaded or cloned repository. | Immediately. |
| Skill ZIP | Uses the extracted portable skill folder. | When the helper or skill is invoked. |

All configuration and hook helpers require Python 3.9 or later. The guided Node launcher requires Node.js 18 or later and can use an explicit interpreter through `AUTONAME_PYTHON`. The currently tested standard `skills` installer has its own [Node.js requirement](https://github.com/vercel-labs/skills#install-a-skill).

### Guided npx

Run the installer directly from GitHub:

```bash
npx --package='github:SuperStevenDing/AutoName' autoname
```

The wizard asks for the target agent and naming format. You can also select a host directly:

```bash
npx --package='github:SuperStevenDing/AutoName' autoname install --host codex
```

From a downloaded or cloned source root, you can also create and run a local package:

```bash
npm pack --ignore-scripts
npx --package=./autoname-skill-0.1.0.tgz autoname
```

The GitHub command downloads from this repository and does not require a separate npm registry release. AutoName uses the [MIT License](LICENSE); npm registry publication is pending. `autoname-skill` is currently the local package identifier, with registry publication disabled by the package's private flag.

### Standard skill manager

From GitHub:

```bash
npx skills add 'SuperStevenDing/AutoName' --skill autoname
```

From a local source checkout:

```bash
npx skills add . --skill autoname
```

The [official installer](https://github.com/vercel-labs/skills/blob/main/docs/commands.md) lets users choose target agents, project or user scope, and symlink or copy installation. Installing files does not register AutoName hooks. Open the target agent and ask it to configure AutoName; the skill guides the format selection and uses `--in-place` to configure its existing canonical files safely.

Keep the hook scope consistent with the chosen installation scope. For a project import, select that project's host configuration root rather than silently registering user-wide hooks. AutoName does not take ownership of the skill manager's files or links. Remove AutoName's hooks with its `uninstall` command before removing the skill through its manager.

### WorkBuddy

The built-in adapter supports on-demand naming and suggestions. From the updated source root, use the user's chosen format and actual host root:

```bash
python skills/autoname/scripts/autoname.py install --host workbuddy --mode on-demand --host-root "<actual-workbuddy-root>" --template "{project}｜{task}" --without-project "{task}" --max-chars 36
```

Replace the root placeholder; the format and length are examples. An existing valid preference file is preserved. No `--adapter` is needed. For an existing private-descriptor installation, retain its original host/data/skill locations and omit `--adapter` when reinstalling from updated source. Skill-manager imports instead configure their updated canonical helper with `--in-place`.

No lifecycle trigger schema has been verified, so automatic mode is rejected. When the conversation ID is initially unavailable, use render, native tool, prepare, then confirm with the returned `conversation.conversationId`. The helper workflow has isolated regression coverage; rerun it in WorkBuddy to verify the installed version. See [the WorkBuddy guide](skills/autoname/references/workbuddy.md). The supplied Windows test reported an npx timeout, so Python/source is the established fallback for that environment; GitHub installation commands remain available for other environments.

### Global command

After creating the local package above, install it as a persistent command:

```bash
npm install --global ./autoname-skill-0.1.0.tgz
autoname
```

The global package exposes the CLI; it does not register agent hooks during npm dependency installation. Run the command to enter setup. To remove it, first use `autoname uninstall --host <host>`, then `npm uninstall --global autoname-skill`.

### Python/source and ZIP

From a repository checkout:

```bash
python3 skills/autoname/scripts/autoname.py
```

From the folder containing an extracted skill ZIP:

```bash
python3 autoname/scripts/autoname.py
```

Both ask for a host and first-run preferences in a terminal. An installing agent can pass `--host`, `--preferences`, and the selected scope explicitly. Non-interactive calls return `setup_required` for missing choices. See [setup](skills/autoname/references/setup.md) and [command reference](skills/autoname/references/commands.md).

## 中文

按使用习惯选择入口。引导式 npx 和 Python 复用同一个配置向导；标准技能安装器先安装文件，再由智能体在首次使用时完成配置。

| 入口 | 作用 | 何时进入配置 |
| --- | --- | --- |
| 引导式 `npx` | 无需永久安装 CLI，直接运行自带安装器。 | 当场进入。 |
| 标准 `npx skills add` | 将 AutoName 安装到所选智能体。 | 首次调用技能时。 |
| 全局 npm 命令 | 安装可重复使用的 `autoname` 命令。 | 运行 `autoname` 时。 |
| Python／源码 | 从下载或克隆的仓库运行安装器。 | 当场进入。 |
| Skill ZIP | 使用解压后的独立技能文件夹。 | 调用工具或技能时。 |

配置和 hook 工具都需要 Python 3.9 或更高版本。引导式 Node 入口需要 Node.js 18 或更高版本，可用 `AUTONAME_PYTHON` 指定解释器。当前验证的标准 `skills` 安装器另有自己的 [Node.js 版本要求](https://github.com/vercel-labs/skills#install-a-skill)。

### 引导式 npx

直接从 GitHub 运行安装器：

```bash
npx --package='github:SuperStevenDing/AutoName' autoname
```

向导会询问安装目标和命名格式，也可以直接指定目标：

```bash
npx --package='github:SuperStevenDing/AutoName' autoname install --host codex
```

也可以在下载或克隆的源码根目录中生成并运行本地包：

```bash
npm pack --ignore-scripts
npx --package=./autoname-skill-0.1.0.tgz autoname
```

GitHub 命令直接从本仓库下载，无需另行发布 npm 注册包。AutoName 采用 [MIT 许可证](LICENSE)，npm 注册包尚未发布。`autoname-skill` 当前是本地包标识，包内的私有标记禁止向 npm 注册表发布。

### 标准技能安装器

从 GitHub 安装：

```bash
npx skills add 'SuperStevenDing/AutoName' --skill autoname
```

从本地仓库安装：

```bash
npx skills add . --skill autoname
```

[官方安装器](https://github.com/vercel-labs/skills/blob/main/docs/commands.md)支持选择目标智能体、项目级或用户级范围，以及符号链接或复制方式。安装文件本身不注册 AutoName hook。打开目标智能体，让它配置 AutoName；技能会引导选择格式，并通过 `--in-place` 安全配置现有的实际技能文件。

hook 的范围应与安装选择一致。项目级导入应选当前项目的宿主配置目录，不静默改成用户全局配置。AutoName 不接管技能安装器管理的文件或链接。卸载时先用 AutoName 的 `uninstall` 移除 hook，再通过技能安装器移除文件。

### WorkBuddy

内置适配支持按需命名和标题建议。在更新后的源码根目录运行，使用用户选择的格式和实际宿主目录：

```bash
python skills/autoname/scripts/autoname.py install --host workbuddy --mode on-demand --host-root "<actual-workbuddy-root>" --template "{project}｜{task}" --without-project "{task}" --max-chars 36
```

替换目录占位符；格式与长度仅为示例。已有有效偏好会保留，无需 `--adapter`。原先使用私有适配描述的安装，应保留原宿主、数据及技能目录，从更新后的源码重新安装时省略 `--adapter`。由技能安装器管理的导入，则更新其实际文件后，用对应工具加 `--in-place` 重新配置。

生命周期触发结构尚未核实，因此拒绝自动模式。如果最初拿不到会话 ID，依次渲染标题、调用原生工具、准备、确认，后两步使用回执中的 `conversation.conversationId`。工具流程已通过隔离回归测试；安装版本仍需在 WorkBuddy 中重新验证，详见 [WorkBuddy 指南](skills/autoname/references/workbuddy.md)。用户提供的 Windows 实测报告了 npx 超时，该环境可沿用 Python／源码安装；其他环境仍可使用 GitHub 安装命令。

### 全局命令

按上面的步骤生成本地包后，将它安装为长期可用的命令：

```bash
npm install --global ./autoname-skill-0.1.0.tgz
autoname
```

全局 npm 安装只提供命令入口，不在依赖安装阶段注册智能体 hook。运行命令后再进入配置。移除时先执行 `autoname uninstall --host <host>`，再执行 `npm uninstall --global autoname-skill`。

### Python／源码与 ZIP

在仓库根目录运行：

```bash
python3 skills/autoname/scripts/autoname.py
```

在 Skill ZIP 解压出的文件夹外运行：

```bash
python3 autoname/scripts/autoname.py
```

两种入口都会在终端询问宿主和首次命名偏好。安装智能体也可以显式传入 `--host`、`--preferences` 及范围参数。非交互调用缺少必要选择时返回 `setup_required`。详见[首次配置](skills/autoname/references/setup.md)和[命令参考](skills/autoname/references/commands.md)。
