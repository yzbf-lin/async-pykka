# async-pykka 发布流程

维护者发布新版本到 PyPI 的操作说明。

## 前置条件

- PyPI 项目 `async-pykka` 已创建。
- GitHub 仓库：`yzbf-lin/async-pykka`。
- 工作流文件已存在：`.github/workflows/publish-pypi.yml`。
- GitHub `pypi` environment 已创建。
- PyPI Trusted Publisher 已配置：
  - Owner：`yzbf-lin`
  - Repository：`async-pykka`
  - Workflow：`publish-pypi.yml`
  - Environment：`pypi`

## 标准发布流程（推荐）

1. 更新 `pyproject.toml` 中的版本号。
2. 本地运行校验：

```bash
uv run ruff check .
uv run pytest -q
```

3. 提交并推送到 `main`：

```bash
git add pyproject.toml
git commit -m "chore: release vX.Y.Z"
git push origin main
```

4. 创建并推送同版本 tag：

```bash
git tag vX.Y.Z
git push origin vX.Y.Z
```

5. 在 GitHub Actions 确认 `publish-pypi` 成功。

说明：tag 版本必须与 `pyproject.toml` 完全一致，例如 `v0.1.5` 对应 `0.1.5`。

## 本地兜底发布（Token 模式）

如果 Actions 发布不可用，可执行：

```bash
export PYPI_TOKEN='pypi-xxxxx'
./scripts/publish_pypi.sh
unset PYPI_TOKEN
```

## 发布后验证

```bash
uv pip install -U async-pykka
python - <<'PY'
import async_pykka
print(async_pykka.__version__ if hasattr(async_pykka, '__version__') else 'installed')
PY
```
