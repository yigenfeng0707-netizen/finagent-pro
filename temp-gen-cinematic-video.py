import asyncio
import json
import subprocess
from pathlib import Path

import edge_tts

OUT = 'finagent-pro-afac2026-demo-cinematic.mp4'
FONT_DIR = Path('fonts')
FONT_TITLE = str(FONT_DIR / 'NotoSansSC-Bold.otf').replace('\\', '/')
FONT_BODY = str(FONT_DIR / 'NotoSansSC.otf').replace('\\', '/')
FONT_SUBTITLE = str(FONT_DIR / 'NotoSansSC-Medium.otf').replace('\\', '/')
FPS = 30
RES = '1920:1080'
SLIDE_DURATION = 31  # seconds per slide; 6*31 - 5*1 = 181s (~3 min)
FADE = 1.0

slides = [
    {
        'img': 'screenshots/01_dashboard.png',
        'title': 'FinAgent Pro 投资仪表盘',
        'subtitle': '多维度资产概览',
        'narration': '欢迎来到 FinAgent Pro。这里是投资仪表盘，为您提供多维度资产概览。左侧导航清晰展示各功能模块，顶部市场指数卡片让您一眼掌握港股通核心指标，股票走势与快速分析面板帮助您快速定位投资机会。',
        'subtitle_text': '欢迎来到 FinAgent Pro。\n这里是投资仪表盘，为您提供多维度资产概览。\n左侧导航清晰展示各功能模块，顶部市场指数卡片\n让您一眼掌握港股通核心指标，股票走势与快速分析\n面板帮助您快速定位投资机会。',
    },
    {
        'img': 'screenshots/02_stock_list.png',
        'title': '港股行情实时追踪',
        'subtitle': '量价与涨跌分布',
        'narration': '港股行情模块实时追踪量价与涨跌分布。您可以按代码或名称搜索股票，查看最新价格、涨跌幅、成交量等关键指标，并结合 AI 状态快速判断市场情绪。',
        'subtitle_text': '港股行情模块实时追踪量价与涨跌分布。\n您可以按代码或名称搜索股票，查看最新价格、\n涨跌幅、成交量等关键指标，\n并结合 AI 状态快速判断市场情绪。',
    },
    {
        'img': 'screenshots/03_agent_chat.png',
        'title': 'Agent 对话',
        'subtitle': '自然语言驱动的智能投顾',
        'narration': '在 Agent 对话页面，您只需用自然语言输入投资需求，例如分析腾讯或十万块保守型配置。系统会自动识别意图，调用后台多 Agent 编排引擎，为您提供专业投顾建议。',
        'subtitle_text': '在 Agent 对话页面，您只需用自然语言\n输入投资需求，例如分析腾讯或\n十万块保守型配置。系统会自动识别意图，\n调用后台多 Agent 编排引擎，\n为您提供专业投顾建议。',
    },
    {
        'img': 'screenshots/04_workbench.png',
        'title': '数字员工工作台',
        'subtitle': '多 Agent 并行编排',
        'narration': '数字员工工作台可视化展示多 Agent 并行编排过程。市场分析师与情绪扫描器并行执行，风险经理与组合顾问串行消费前序结果，DAG 依赖图与工具调用日志让每一步都清晰可见。',
        'subtitle_text': '数字员工工作台可视化展示\n多 Agent 并行编排过程。\n市场分析师与情绪扫描器并行执行，\n风险经理与组合顾问串行消费前序结果，\nDAG 依赖图与工具调用日志让每一步都清晰可见。',
    },
    {
        'img': 'screenshots/05_dashboard_full.png',
        'title': '组合分析',
        'subtitle': '收益、风险、回撤全景',
        'narration': '组合分析页面提供收益、风险、回撤全景视图。资产列表与饼图展示配置详情，马科维茨最优配置与完整推理过程帮助您理解每一个投资建议背后的逻辑。',
        'subtitle_text': '组合分析页面提供收益、风险、回撤全景视图。\n资产列表与饼图展示配置详情，\n马科维茨最优配置与完整推理过程\n帮助您理解每一个投资建议背后的逻辑。',
    },
    {
        'img': 'screenshots/06_risk_page.png',
        'title': '风险评估',
        'subtitle': 'VaR 与压力测试',
        'narration': '风险评估中心聚焦 VaR 与压力测试。风险仪表盘直观展示当前组合风险等级，CVaR、夏普比率与年化收益等统计指标，为您的投资决策提供量化风控依据。',
        'subtitle_text': '风险评估中心聚焦 VaR 与压力测试。\n风险仪表盘直观展示当前组合风险等级，\nCVaR、夏普比率与年化收益等统计指标，\n为您的投资决策提供量化风控依据。',
    },
]


def wrap_text(text, max_chars=34):
    lines = []
    current = ''
    for ch in text:
        current += ch
        if len(current) >= max_chars:
            lines.append(current)
            current = ''
    if current:
        lines.append(current)
    return '\n'.join(lines)


async def gen_audio(text, out_path):
    communicate = edge_tts.Communicate(text, voice='zh-CN-XiaoxiaoNeural', rate='-8%')
    await communicate.save(out_path)


def audio_duration(path):
    r = subprocess.run(
        ['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'json', path],
        capture_output=True, text=True, check=True
    )
    return float(json.loads(r.stdout)['format']['duration'])


def pad_audio(audio_path, target_duration, out_path):
    # edge-tts MP3 has a quirky stream; convert to WAV first, then pad.
    wav_path = str(Path(out_path).with_suffix('.tmp.wav'))
    subprocess.run([
        'ffmpeg', '-y', '-i', audio_path,
        '-acodec', 'pcm_s16le', '-ar', '48000', '-ac', '1',
        wav_path,
    ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.run([
        'ffmpeg', '-y', '-i', wav_path,
        '-af', f'apad=pad_dur={target_duration}',
        '-t', str(target_duration),
        '-acodec', 'pcm_s16le', '-ar', '48000', '-ac', '1',
        out_path,
    ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    Path(wav_path).unlink(missing_ok=True)


def build_slide(img, audio_path, title, subtitle, subtitle_text, subtitle_file, out_path):
    Path(subtitle_file).write_text(subtitle_text, encoding='utf-8')
    frames = int(SLIDE_DURATION * FPS)
    title_s = title.replace("'", "'\\''")
    subtitle_s = subtitle.replace("'", "'\\''")

    # subtle pan: start center, drift slightly to top-right
    zoom_expr = f"'1+0.12*time/{SLIDE_DURATION}'"
    x_expr = f"'(iw-iw/zoom)*(0.45+0.1*time/{SLIDE_DURATION})'"
    y_expr = f"'(ih-ih/zoom)*(0.45+0.05*time/{SLIDE_DURATION})'"

    vf = (
        f"[0:v]scale={RES}:force_original_aspect_ratio=decrease,"
        f"pad={RES}:(ow-iw)/2:(oh-ih)/2:black,"
        f"zoompan=z={zoom_expr}:d={frames}:s=1920x1080:fps={FPS}:x={x_expr}:y={y_expr},"
        f"fade=t=in:st=0:d={FADE},fade=t=out:st={SLIDE_DURATION-FADE}:d={FADE},"
        f"drawtext=fontfile={FONT_TITLE}:text='{title_s}':fontcolor=white:fontsize=72:"
        f"borderw=8:bordercolor=#000000@0.75:x=(w-text_w)/2:y=100,"
        f"drawtext=fontfile={FONT_BODY}:text='{subtitle_s}':fontcolor=#FFD700:fontsize=46:"
        f"borderw=6:bordercolor=#000000@0.65:x=(w-text_w)/2:y=190,"
        f"drawtext=fontfile={FONT_SUBTITLE}:textfile={subtitle_file}:fontcolor=white:fontsize=34:"
        f"borderw=4:bordercolor=#000000@0.75:x=(w-text_w)/2:y=h-text_h-100:"
        f"line_spacing=12:box=1:boxcolor=#000000@0.35:boxborderw=16[v]"
    )

    cmd = [
        'ffmpeg', '-y', '-loop', '1', '-i', img, '-i', audio_path,
        '-filter_complex', vf,
        '-map', '[v]', '-map', '1:a',
        '-c:v', 'libx264', '-preset', 'slow', '-crf', '16',
        '-c:a', 'aac', '-b:a', '192k', '-ar', '48000',
        '-pix_fmt', 'yuv420p', '-r', str(FPS), '-t', str(SLIDE_DURATION),
        '-movflags', '+faststart',
        out_path,
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL)


async def main():
    tmp_dir = Path('tmp_video_segments')
    tmp_dir.mkdir(exist_ok=True)

    segment_files = []
    for i, slide in enumerate(slides, 1):
        audio_raw = tmp_dir / f'slide{i:02d}_raw.mp3'
        audio_padded = tmp_dir / f'slide{i:02d}.wav'
        video_path = tmp_dir / f'slide{i:02d}.mp4'
        subtitle_file = tmp_dir / f'slide{i:02d}_sub.txt'

        print(f'Generating audio for slide {i}...')
        await gen_audio(slide['narration'], str(audio_raw))

        dur = audio_duration(str(audio_raw))
        print(f'Slide {i} raw audio duration: {dur:.2f}s')

        print(f'Padding audio to {SLIDE_DURATION}s...')
        pad_audio(str(audio_raw), SLIDE_DURATION, str(audio_padded))

        print(f'Building slide {i} video...')
        build_slide(
            slide['img'], str(audio_padded),
            slide['title'], slide['subtitle'], slide['subtitle_text'],
            str(subtitle_file).replace('\\', '/'),
            str(video_path)
        )
        segment_files.append(str(video_path))

    # Crossfade concat using filter_complex
    inputs = []
    for seg in segment_files:
        inputs.extend(['-i', seg])

    n = len(segment_files)
    v_labels = [f'{i}:v' for i in range(n)]
    a_labels = [f'{i}:a' for i in range(n)]

    v_chain = []
    prev_v = v_labels[0]
    prev_dur = SLIDE_DURATION
    for i in range(1, n):
        offset = prev_dur - FADE
        out_v = f'vt{i}' if i < n - 1 else 'outv'
        v_chain.append(f"[{prev_v}][{v_labels[i]}]xfade=transition=fade:duration={FADE}:offset={offset}[{out_v}]")
        prev_v = out_v
        prev_dur = offset + SLIDE_DURATION

    a_chain = []
    prev_a = a_labels[0]
    for i in range(1, n):
        out_a = f'at{i}' if i < n - 1 else 'outa'
        a_chain.append(f"[{prev_a}][{a_labels[i]}]acrossfade=d={FADE}[{out_a}]")
        prev_a = out_a

    filter_complex = ';'.join(v_chain + a_chain)

    cmd = [
        'ffmpeg', '-y', *inputs,
        '-filter_complex', filter_complex,
        '-map', '[outv]', '-map', '[outa]',
        '-c:v', 'libx264', '-preset', 'slow', '-crf', '16',
        '-c:a', 'aac', '-b:a', '192k', '-ar', '48000',
        '-pix_fmt', 'yuv420p', '-r', str(FPS),
        '-movflags', '+faststart',
        OUT,
    ]
    print('Crossfading segments...')
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL)

    print(f'Done: {OUT}')


if __name__ == '__main__':
    asyncio.run(main())
