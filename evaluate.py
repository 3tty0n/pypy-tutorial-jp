import subprocess
import time
import numpy as np
import matplotlib.pyplot as plt

# 実行するコマンドのリスト
commands = [
    "./example2-c mandel.b",
    "./example3-c mandel.b",
    "./example4-c mandel.b",
    "./example5-c mandel.b"
]

# コマンドの実行回数
n = 5

# 実行時間を記録するリスト
execution_times = []

for cmd in commands:
    times = []
    for _ in range(n):
        start_time = time.time()
        try:
            subprocess.run(cmd, shell=True, check=True)
        except subprocess.CalledProcessError as e:
            print(f"Error while executing '{cmd}': {e}")
        end_time = time.time()
        times.append(end_time - start_time)
    execution_times.append(times)

# 平均と標準偏差を計算
means = [np.mean(times) for times in execution_times]
std_devs = [np.std(times) for times in execution_times]

# グラフの描画
plt.figure(figsize=(10, 6))
plt.bar(range(len(commands)), means, yerr=std_devs, capsize=5, alpha=0.7, color='skyblue')
plt.xticks(range(len(commands)), commands, rotation=45, ha="right")
plt.xlabel("Commands")
plt.ylabel("Execution Time (seconds)")
plt.title("Average Execution Time with Error Bars (Standard Deviation)")
plt.tight_layout()

# グラフを画像として保存
plt.savefig("execution_time_plot.png")
