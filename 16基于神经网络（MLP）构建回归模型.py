import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.neural_network import MLPRegressor
from sklearn.metrics import r2_score
from sklearn.preprocessing import StandardScaler
import matplotlib
import matplotlib.pyplot as plt

# ===================== 核心配置：强制交互式后端 =====================
# 强制使用TkAgg交互式后端（确保弹窗显示，Python默认自带）
matplotlib.use('TkAgg')
# 开启交互式模式
plt.ion()
print(f"📊 Matplotlib后端：{matplotlib.get_backend()}（交互式窗口显示，手动关闭后继续）")

# 全局配置
DATA_PATH = "C:/Users/thv/Desktop/fdc (1).xlsx"  # 数据路径
TEST_SIZE = 0.2
RANDOM_STATE = 42
FIG_SIZE = (12, 6)  # 图表尺寸
PARAM_COMBINATIONS = [
    {"solver": "lbfgs", "alpha": 0.0001, "hidden_layer_sizes": (100,), "max_iter": 3000, "tol": 1e-3},
    {"solver": "sgd", "alpha": 0.001, "hidden_layer_sizes": (50,), "max_iter": 3000,
     "momentum": 0.9, "learning_rate": "adaptive", "learning_rate_init": 0.01},
    {"solver": "adam", "alpha": 0.00001, "hidden_layer_sizes": (150,), "max_iter": 3000,
     "learning_rate_init": 0.001}
]
COLOR_MAP = {"TSS": "blue", "RSS": "red", "ESS": "green", "R²": "orange"}


# ===================== 工具函数 =====================
def load_and_split_data(data_path, test_size, random_state):
    """加载数据并划分训练/测试集，包含数据校验"""
    try:
        data = pd.read_excel(data_path, engine="openpyxl")
    except FileNotFoundError:
        raise FileNotFoundError(f"❌ 数据文件未找到，请检查路径：{data_path}")
    except Exception as e:
        raise Exception(f"❌ 加载数据失败：{str(e)}")

    required_cols = ['AT', 'V', 'AP', 'RH', 'PE']
    missing_cols = [col for col in required_cols if col not in data.columns]
    if missing_cols:
        raise ValueError(f"❌ 数据缺失必要列：{missing_cols}")

    X = data[['AT', 'V', 'AP', 'RH']]
    y = data['PE']
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=random_state
    )

    # 特征标准化（MLP关键）
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    print(f"✅ 数据加载完成！")
    print(f"   训练集样本数：{len(X_train)}, 测试集样本数：{len(X_test)}")
    return X_train_scaled, X_test_scaled, y_train, y_test, scaler


def train_mlp_model(X_train, y_train, params, random_state):
    """训练MLP回归模型，优化收敛性"""
    model_kwargs = {
        "solver": params["solver"],
        "alpha": params["alpha"],
        "hidden_layer_sizes": params["hidden_layer_sizes"],
        "max_iter": params["max_iter"],
        "random_state": random_state,
        "verbose": False,
        "early_stopping": True,
        "validation_fraction": 0.1,
        "n_iter_no_change": 50
    }
    if "tol" in params:
        model_kwargs["tol"] = params["tol"]
    if "momentum" in params:
        model_kwargs["momentum"] = params["momentum"]
    if "learning_rate" in params:
        model_kwargs["learning_rate"] = params["learning_rate"]
    if "learning_rate_init" in params:
        model_kwargs["learning_rate_init"] = params["learning_rate_init"]

    model = MLPRegressor(**model_kwargs)
    model.fit(X_train, y_train)

    # 收敛状态提示
    if model.n_iter_ >= model.max_iter:
        print(f"⚠️  警告：{params['solver']} 模型未收敛（迭代次数达上限 {model.max_iter}）")
    elif model.early_stopping:
        print(f"✅ {params['solver']} 模型早停收敛（实际迭代次数：{model.n_iter_}）")
    else:
        print(f"✅ {params['solver']} 模型正常收敛（实际迭代次数：{model.n_iter_}）")

    return model


def calculate_metrics(y_test, y_pred):
    """计算回归评估指标"""
    y_mean = np.mean(y_test)
    TSS = np.sum((y_test - y_mean) ** 2)
    RSS = np.sum((y_test - y_pred) ** 2)
    ESS = TSS - RSS
    r2 = r2_score(y_test, y_pred)
    rmse = np.sqrt(np.mean((y_test - y_pred) ** 2))
    return {"TSS": TSS, "RSS": RSS, "ESS": ESS, "R²": r2, "RMSE": rmse}


def plot_model_results(idx, params, metrics, fig_size):
    """交互式显示图表，手动关闭后继续"""
    # 创建新的图表（避免复用画布导致混乱）
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=fig_size, dpi=100)
    fig.suptitle(f"Model {idx + 1} - {params['solver']} Optimizer", fontsize=14, fontweight='bold')

    # 子图1：参数信息
    param_text = (
        f"Parameter Configuration\n"
        f"Solver: {params['solver']}\n"
        f"Alpha (L2): {params['alpha']}\n"
        f"Hidden Layers: {params['hidden_layer_sizes']}\n"
        f"Max Iterations: {params['max_iter']}\n"
        f"R² Score: {metrics['R²']:.4f}\n"
        f"RMSE: {metrics['RMSE']:.2f}"
    )
    ax1.text(0.05, 0.95, param_text, fontsize=10, verticalalignment='top',
             bbox=dict(boxstyle="round,pad=0.3", facecolor="lightgray", alpha=0.5))
    ax1.axis("off")
    ax1.set_title("Model Parameters", fontsize=12, fontweight='bold')

    # 子图2：评估指标（双Y轴）
    labels = ["TSS", "RSS", "ESS", "R²"]
    values = [metrics["TSS"], metrics["RSS"], metrics["ESS"], metrics["R²"]]
    colors = [COLOR_MAP[label] for label in labels]

    # 绘制TSS/RSS/ESS（左轴）
    ax2.bar(labels[:-1], values[:-1], color=colors[:-1], alpha=0.7, width=0.6)
    ax2.set_ylabel("TSS/RSS/ESS Value", fontsize=10)
    ax2.ticklabel_format(style='scientific', axis='y', scilimits=(0, 0))
    ax2.grid(axis='y', alpha=0.3)

    # 绘制R²（右轴）
    ax2_twin = ax2.twinx()
    ax2_twin.bar(labels[-1], values[-1], color=colors[-1], alpha=0.7, width=0.6)
    ax2_twin.set_ylabel("R² Score", fontsize=10, color=COLOR_MAP["R²"])
    ax2_twin.tick_params(axis='y', labelcolor=COLOR_MAP["R²"])
    ax2_twin.set_ylim(0, 1.1)
    ax2.set_title("Regression Metrics", fontsize=12, fontweight='bold')

    # 调整布局
    plt.tight_layout()

    # 关键：阻塞显示，直到手动关闭窗口
    plt.show(block=True)
    # 关闭当前图表，释放资源
    plt.close(fig)


# ===================== 主流程 =====================
def main():
    try:
        # 1. 加载数据
        X_train, X_test, y_train, y_test, scaler = load_and_split_data(
            DATA_PATH, TEST_SIZE, RANDOM_STATE
        )

        # 2. 训练模型并交互式显示图表
        all_results = []
        for idx, params in enumerate(PARAM_COMBINATIONS):
            print(f"\n========== 训练第 {idx + 1} 组模型 ==========")
            model = train_mlp_model(X_train, y_train, params, RANDOM_STATE)
            y_pred = model.predict(X_test)
            metrics = calculate_metrics(y_test, y_pred)

            all_results.append({
                "model_idx": idx + 1,
                "solver": params["solver"],
                "r2": metrics["R²"],
                "rmse": metrics["RMSE"],
                "metrics": metrics,
                "params": params
            })

            # 交互式显示图表（手动关闭后继续）
            print(f"🖼️  正在显示模型{idx + 1}的图表，请手动关闭窗口继续...")
            plot_model_results(idx, params, metrics, FIG_SIZE)

        # 3. 结果汇总
        print("\n" + "=" * 50)
        print("📈 所有模型性能汇总")
        print("=" * 50)
        for res in all_results:
            print(f"模型{res['model_idx']:d} | 优化器：{res['solver']:6s} | R²：{res['r2']:.4f} | RMSE：{res['rmse']:.2f}")

        # 4. 最优模型
        best_model = max(all_results, key=lambda x: x["r2"])
        print("\n🏆 最优模型信息")
        print(f"模型编号：{best_model['model_idx']}")
        print(f"优化器：{best_model['solver']}")
        print(f"R²得分：{best_model['r2']:.4f}")
        print(f"RMSE：{best_model['rmse']:.2f}")
        print(f"参数：{best_model['params']}")

    except Exception as e:
        print(f"\n❌ 程序执行失败：{str(e)}")
        return


# ===================== 执行入口 =====================
if __name__ == "__main__":
    main()
    print("\n✅ 程序执行完毕！")