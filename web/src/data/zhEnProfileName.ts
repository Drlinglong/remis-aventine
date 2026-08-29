import type { ZhEnPreviewProfile } from '../types/zhEnPreview';

const DISPLAY_NAMES: Record<string, string> = {
  'openai/gpt-5.6-sol-pro': 'GPT-5.6 Sol Pro',
  'qwen/qwen3.8-max': 'Qwen 3.8 Max',
  'meituan/longcat-2.0': 'LongCat 2.0',
  'google/gemini-3.7-flash': 'Gemini 3.7 Flash',
  'deepseek/deepseek-v4-pro-0813': 'DeepSeek V4 Pro',
  'moonshotai/kimi-k3': 'Kimi K3',
  'openai/gpt-5.6-terra': 'GPT-5.6 Terra',
  'x-ai/grok-4.6': 'Grok 4.6',
  'tencent/hy3': 'HY3',
  'meta/muse-spark-1.2': 'Muse Spark 1.2',
  'minimax/minimax-m3': 'MiniMax M3',
  'openai/gpt-5.6-luna': 'GPT-5.6 Luna',
  'qwen/qwen3.8-27b': 'Qwen 3.8 27B',
  'deepseek/deepseek-v4-flash-0731': 'DeepSeek V4 Flash',
  'xiaomi/mimo-v2.5': 'MiMo V2.5',
  'upstage/solar-pro4': 'Solar Pro 4',
  'nvidia/nemotron-3.5-lightning': 'Nemotron 3.5 Lightning',
};

export function zhEnProfileName(profile: ZhEnPreviewProfile): string {
  return DISPLAY_NAMES[profile.model_id] ?? profile.model_id.split('/').pop() ?? profile.model_id;
}
