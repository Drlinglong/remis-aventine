import evidence from '../../public/data/v03-execution-settings.json';
import type { ZhEnPreviewProfile } from '../types/zhEnPreview';

export interface ExecutionSettings {
  model_id: string;
  reasoning: string;
  max_output_tokens: number;
  provider: string;
  runner_sha256: string;
  generation?: {
    calls: number;
    entries: number;
    raw_contract_pass: number;
    final_contract_pass: number;
    empty_responses: number;
    finish_stop: number;
  };
}

/** Look up the measured recipe, never infer settings from a model's name. */
export function executionSettings(profile: ZhEnPreviewProfile): ExecutionSettings | undefined {
  const setting = (evidence.identities as Record<string, ExecutionSettings>)[profile.execution_identity_sha256];
  return setting?.model_id === profile.model_id ? setting : undefined;
}

export function reasoningLabel(profile: ZhEnPreviewProfile, zh = false): string {
  const value = executionSettings(profile)?.reasoning;
  if (!value) return zh ? '未记录' : 'unrecorded';
  if (value === 'unspecified') return zh ? '默认配置' : 'default';
  if (value === 'on') return zh ? '推理开启' : 'thinking on';
  if (value === 'off') return zh ? '推理关闭' : 'thinking off';
  return value;
}
