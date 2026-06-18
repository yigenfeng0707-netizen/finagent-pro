import subprocess

slides = [
    ('screenshots/01_dashboard.png', 'FinAgent Pro 投资仪表盘 - 多维度资产概览'),
    ('screenshots/02_stock_list.png', '港股行情实时追踪 - 量价与涨跌分布'),
    ('screenshots/03_agent_chat.png', 'Agent 对话 - 自然语言驱动的智能投顾'),
    ('screenshots/04_workbench.png', '数字员工工作台 - 多 Agent 并行编排'),
    ('screenshots/05_dashboard_full.png', '组合分析 - 收益、风险、回撤全景'),
    ('screenshots/06_risk_page.png', '风险评估 - VaR 与压力测试'),
]

inputs = []
filter_parts = []
fontfile = 'C\\:/Windows/Fonts/msyh.ttc'
DURATION = 31  # seconds per slide; 6*31 - 5*1 = 181s (~3 min)

for i, (img, text) in enumerate(slides):
    inputs.extend(['-i', img])
    draw = (
        f"[{i}:v]loop=loop=-1:size=1:start=0,trim=duration={DURATION},fps=30,"
        f"scale=1280:720:force_original_aspect_ratio=decrease,"
        f"pad=1280:720:(ow-iw)/2:(oh-ih)/2,"
        f"drawtext=fontfile={fontfile}:text='{text}':"
        f"fontcolor=white:fontsize=44:borderw=4:bordercolor=black@0.5:"
        f"x=(w-text_w)/2:y=h-text_h-80:enable='between(t\\,1\\,{DURATION-1})'[v{i}]"
    )
    filter_parts.append(draw)

# Build xfade chain; offset must start one second before the previous output ends.
chain = []
prev = 'v0'
prev_duration = DURATION
for i in range(1, len(slides)):
    offset = prev_duration - 1
    out = f'x{i-1}' if i < len(slides)-1 else 'outv'
    chain.append(f"[{prev}][v{i}]xfade=transition=fade:duration=1:offset={offset}[{out}]")
    prev = f'x{i-1}'
    prev_duration = offset + DURATION  # = prev_duration + DURATION - 1

filter_complex = ';'.join(filter_parts + chain)
cmd = [
    'ffmpeg', '-y',
    *inputs,
    '-filter_complex', filter_complex,
    '-map', '[outv]',
    '-c:v', 'libx264',
    '-pix_fmt', 'yuv420p',
    '-movflags', '+faststart',
    'finagent-pro-afac2026-demo.mp4',
]

print('Running...')
subprocess.run(cmd, check=True)
print('Generated finagent-pro-afac2026-demo.mp4')
