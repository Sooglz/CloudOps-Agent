# Kubernetes 常见故障排查手册

## 一、Pod 状态异常排查

### 1. Pod 一直处于 CrashLoopBackOff

**现象**：`kubectl get pods` 显示 Pod 状态为 CrashLoopBackOff，重启次数持续增加。

**常见原因**：
- 容器启动后立即退出（启动命令错误、缺少依赖）
- 应用启动时抛出异常（配置缺失、端口被占用）
- 健康检查探针配置错误（livenessProbe 配置不当）
- 资源不足（内存溢出 OOM）

**排查步骤**：
1. 查看 Pod 详情：`kubectl describe pod <pod名>`
2. 查看容器日志：`kubectl logs <pod名> --previous`（查看上一次崩溃的日志）
3. 检查退出码：`kubectl get pod <pod名> -o yaml` 中查看 lastState.exitCode
4. 检查资源限制：确认是否因内存不足被 OOM Killer 杀死

### 2. Pod 一直处于 Pending

**现象**：Pod 创建后一直处于 Pending 状态，无法调度到节点。

**常见原因**：
- 集群资源不足（CPU/内存不够）
- 节点亲和性/污点（taint）不匹配
- PVC 无法绑定（存储卷问题）
- 镜像拉取失败

**排查步骤**：
1. `kubectl describe pod <pod名>` 查看 Events 事件
2. 检查节点资源：`kubectl describe node <节点名>`
3. 检查是否设置了 nodeSelector 或容忍度（tolerations）

## 二、Service 无法访问排查

### 现象
集群内无法通过 Service 访问到 Pod。

### 排查步骤
1. 确认 Service 的 selector 与 Pod 的 label 是否匹配
2. 确认 Service 的端口与 Pod 的 containerPort 是否对应
3. 检查 Endpoints：`kubectl get endpoints <service名>` 是否有后端地址
4. 检查 kube-proxy 是否正常运行

## 三、镜像拉取失败 ImagePullBackOff

### 常见原因
- 镜像名称或 tag 写错
- 私有仓库需要认证（imagePullSecret 未配置）
- 网络无法访问镜像仓库

### 解决
1. 检查镜像名：`kubectl describe pod <pod名>` 查看具体错误
2. 私有仓库配置 imagePullSecret
3. 本地先 `docker pull` 测试镜像是否可拉取
