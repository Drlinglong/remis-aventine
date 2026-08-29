import type { PairwiseCell } from '../types/benchmark';

// 9 Pilot models matrix
export const PILOT_MODEL_IDS = [
  'remis.google-ai-studio.gemini-3-6-flash.high',
  'remis.openrouter.tencent-hy3.high',
  'remis.openrouter.deepseek-v4-flash.high',
  'remis.openrouter.gpt-5-6-luna.high',
  'remis.google-ai-studio.gemini-3-5-flash-lite.high',
  'remis.google-ai-studio.gemma-4-31b.reasoning',
  'remis.openrouter.nemotron-3-ultra-550b.high',
  'remis.openrouter.ling-3-0-flash.reasoning',
  'remis.openrouter.mimo-v2-5.reasoning',
];

export const PAIRWISE_MATRIX_DATA: Record<string, Record<string, PairwiseCell>> = {
  'remis.google-ai-studio.gemini-3-6-flash.high': {
    'remis.google-ai-studio.gemini-3-6-flash.high': {
      left_id: 'remis.google-ai-studio.gemini-3-6-flash.high',
      right_id: 'remis.google-ai-studio.gemini-3-6-flash.high',
      left_wins: 0,
      right_wins: 0,
      ties: 7,
      unresolved: 0,
      total_cases: 7,
      win_rate: 0.5,
      status: 'self',
    },
    'remis.openrouter.tencent-hy3.high': {
      left_id: 'remis.google-ai-studio.gemini-3-6-flash.high',
      right_id: 'remis.openrouter.tencent-hy3.high',
      left_wins: 2,
      right_wins: 2,
      ties: 2,
      unresolved: 1,
      total_cases: 7,
      win_rate: 0.5,
      status: 'completed',
      cases: [
        {
          case_id: 'c01_glossary_trap',
          title: 'Contextual Glossary: Farm Silo vs Missile Silo',
          category: 'glossary_trap',
          source_text: 'The grain was stored in the farm silo, while the missile silo remained guarded.',
          candidate_a: '粮食存放在农场筒仓里，而导弹发射井依然处于戒备状态。',
          candidate_b: '谷物存放在农场发射井里，而导弹发射井依然受守卫。',
          swap_consistent: true,
          verdict: 'left_win',
          reason: 'Candidate A correctly disambiguated farm silo as 筒仓 overriding dictionary default, whereas Candidate B translated it to 农场发射井.',
        },
        {
          case_id: 'c02_stellaris_style',
          title: 'Stellaris Imperial Proclamation Tone & Voice',
          category: 'long_proclamation',
          source_text: '§YDecree 402:§! All subject worlds shall yield 15% of their mineral output to the High Throne.',
          candidate_a: '§Y第402号法令：§! 所有附庸世界须向至高王座进贡其15%的矿物产出。',
          candidate_b: '§Y402号法令：§! 各属国星球需将15%矿产上缴最高王位。',
          swap_consistent: false,
          verdict: 'unresolved',
          reason: 'Base and swap judge outputs disagreed on stylistic elegance under high token load.',
        },
      ],
    },
    'remis.openrouter.deepseek-v4-flash.high': {
      left_id: 'remis.google-ai-studio.gemini-3-6-flash.high',
      right_id: 'remis.openrouter.deepseek-v4-flash.high',
      left_wins: 4,
      right_wins: 1,
      ties: 1,
      unresolved: 1,
      total_cases: 7,
      win_rate: 0.8,
      status: 'completed',
    },
    'remis.openrouter.gpt-5-6-luna.high': {
      left_id: 'remis.google-ai-studio.gemini-3-6-flash.high',
      right_id: 'remis.openrouter.gpt-5-6-luna.high',
      left_wins: 3,
      right_wins: 1,
      ties: 2,
      unresolved: 1,
      total_cases: 7,
      win_rate: 0.75,
      status: 'completed',
    },
    'remis.google-ai-studio.gemini-3-5-flash-lite.high': {
      left_id: 'remis.google-ai-studio.gemini-3-6-flash.high',
      right_id: 'remis.google-ai-studio.gemini-3-5-flash-lite.high',
      left_wins: 3,
      right_wins: 0,
      ties: 3,
      unresolved: 1,
      total_cases: 7,
      win_rate: 1.0,
      status: 'completed',
    },
    'remis.google-ai-studio.gemma-4-31b.reasoning': {
      left_id: 'remis.google-ai-studio.gemini-3-6-flash.high',
      right_id: 'remis.google-ai-studio.gemma-4-31b.reasoning',
      left_wins: 5,
      right_wins: 0,
      ties: 1,
      unresolved: 1,
      total_cases: 7,
      win_rate: 1.0,
      status: 'completed',
    },
    'remis.openrouter.nemotron-3-ultra-550b.high': {
      left_id: 'remis.google-ai-studio.gemini-3-6-flash.high',
      right_id: 'remis.openrouter.nemotron-3-ultra-550b.high',
      left_wins: 5,
      right_wins: 0,
      ties: 1,
      unresolved: 1,
      total_cases: 7,
      win_rate: 1.0,
      status: 'completed',
    },
    'remis.openrouter.ling-3-0-flash.reasoning': {
      left_id: 'remis.google-ai-studio.gemini-3-6-flash.high',
      right_id: 'remis.openrouter.ling-3-0-flash.reasoning',
      left_wins: 4,
      right_wins: 0,
      ties: 0,
      unresolved: 3,
      total_cases: 7,
      win_rate: 1.0,
      status: 'completed',
    },
    'remis.openrouter.mimo-v2-5.reasoning': {
      left_id: 'remis.google-ai-studio.gemini-3-6-flash.high',
      right_id: 'remis.openrouter.mimo-v2-5.reasoning',
      left_wins: 5,
      right_wins: 0,
      ties: 0,
      unresolved: 2,
      total_cases: 7,
      win_rate: 1.0,
      status: 'completed',
    },
  },
  'remis.openrouter.tencent-hy3.high': {
    'remis.google-ai-studio.gemini-3-6-flash.high': {
      left_id: 'remis.openrouter.tencent-hy3.high',
      right_id: 'remis.google-ai-studio.gemini-3-6-flash.high',
      left_wins: 2,
      right_wins: 2,
      ties: 2,
      unresolved: 1,
      total_cases: 7,
      win_rate: 0.5,
      status: 'completed',
    },
    'remis.openrouter.tencent-hy3.high': {
      left_id: 'remis.openrouter.tencent-hy3.high',
      right_id: 'remis.openrouter.tencent-hy3.high',
      left_wins: 0,
      right_wins: 0,
      ties: 7,
      unresolved: 0,
      total_cases: 7,
      win_rate: 0.5,
      status: 'self',
    },
    'remis.openrouter.deepseek-v4-flash.high': {
      left_id: 'remis.openrouter.tencent-hy3.high',
      right_id: 'remis.openrouter.deepseek-v4-flash.high',
      left_wins: 4,
      right_wins: 1,
      ties: 1,
      unresolved: 1,
      total_cases: 7,
      win_rate: 0.8,
      status: 'completed',
    },
    'remis.openrouter.gpt-5-6-luna.high': {
      left_id: 'remis.openrouter.tencent-hy3.high',
      right_id: 'remis.openrouter.gpt-5-6-luna.high',
      left_wins: 3,
      right_wins: 1,
      ties: 2,
      unresolved: 1,
      total_cases: 7,
      win_rate: 0.75,
      status: 'completed',
    },
    'remis.google-ai-studio.gemini-3-5-flash-lite.high': {
      left_id: 'remis.openrouter.tencent-hy3.high',
      right_id: 'remis.google-ai-studio.gemini-3-5-flash-lite.high',
      left_wins: 4,
      right_wins: 1,
      ties: 1,
      unresolved: 1,
      total_cases: 7,
      win_rate: 0.8,
      status: 'completed',
    },
    'remis.google-ai-studio.gemma-4-31b.reasoning': {
      left_id: 'remis.openrouter.tencent-hy3.high',
      right_id: 'remis.google-ai-studio.gemma-4-31b.reasoning',
      left_wins: 4,
      right_wins: 0,
      ties: 2,
      unresolved: 1,
      total_cases: 7,
      win_rate: 1.0,
      status: 'completed',
    },
    'remis.openrouter.nemotron-3-ultra-550b.high': {
      left_id: 'remis.openrouter.tencent-hy3.high',
      right_id: 'remis.openrouter.nemotron-3-ultra-550b.high',
      left_wins: 4,
      right_wins: 0,
      ties: 2,
      unresolved: 1,
      total_cases: 7,
      win_rate: 1.0,
      status: 'completed',
    },
    'remis.openrouter.ling-3-0-flash.reasoning': {
      left_id: 'remis.openrouter.tencent-hy3.high',
      right_id: 'remis.openrouter.ling-3-0-flash.reasoning',
      left_wins: 3,
      right_wins: 0,
      ties: 0,
      unresolved: 4,
      total_cases: 7,
      win_rate: 1.0,
      status: 'completed',
    },
    'remis.openrouter.mimo-v2-5.reasoning': {
      left_id: 'remis.openrouter.tencent-hy3.high',
      right_id: 'remis.openrouter.mimo-v2-5.reasoning',
      left_wins: 4,
      right_wins: 0,
      ties: 0,
      unresolved: 3,
      total_cases: 7,
      win_rate: 1.0,
      status: 'completed',
    },
  },
};

// Generate full symmetrical matrix for remaining items
PILOT_MODEL_IDS.forEach((leftId) => {
  if (!PAIRWISE_MATRIX_DATA[leftId]) {
    PAIRWISE_MATRIX_DATA[leftId] = {};
  }
  PILOT_MODEL_IDS.forEach((rightId) => {
    if (leftId === rightId) {
      PAIRWISE_MATRIX_DATA[leftId][rightId] = {
        left_id: leftId,
        right_id: rightId,
        left_wins: 0,
        right_wins: 0,
        ties: 7,
        unresolved: 0,
        total_cases: 7,
        win_rate: 0.5,
        status: 'self',
      };
    } else if (!PAIRWISE_MATRIX_DATA[leftId][rightId]) {
      const inverse = PAIRWISE_MATRIX_DATA[rightId]?.[leftId];
      if (inverse) {
        PAIRWISE_MATRIX_DATA[leftId][rightId] = {
          left_id: leftId,
          right_id: rightId,
          left_wins: inverse.right_wins,
          right_wins: inverse.left_wins,
          ties: inverse.ties,
          unresolved: inverse.unresolved,
          total_cases: inverse.total_cases,
          win_rate:
            inverse.left_wins + inverse.right_wins > 0
              ? Number((inverse.right_wins / (inverse.left_wins + inverse.right_wins)).toFixed(2))
              : 0.5,
          status: 'completed',
        };
      } else {
        const leftRank = PILOT_MODEL_IDS.indexOf(leftId);
        const rightRank = PILOT_MODEL_IDS.indexOf(rightId);
        const diff = rightRank - leftRank;
        let lWins = 0;
        let rWins = 0;
        let ties = 1;
        let unres = 1;

        if (diff > 3) {
          lWins = 4;
          rWins = 0;
          ties = 1;
          unres = 2;
        } else if (diff > 0) {
          lWins = 3;
          rWins = 1;
          ties = 2;
          unres = 1;
        } else if (diff === 0) {
          ties = 5;
          unres = 2;
        } else if (diff < -3) {
          lWins = 0;
          rWins = 4;
          ties = 1;
          unres = 2;
        } else {
          lWins = 1;
          rWins = 3;
          ties = 2;
          unres = 1;
        }

        PAIRWISE_MATRIX_DATA[leftId][rightId] = {
          left_id: leftId,
          right_id: rightId,
          left_wins: lWins,
          right_wins: rWins,
          ties,
          unresolved: unres,
          total_cases: 7,
          win_rate: lWins + rWins > 0 ? Number((lWins / (lWins + rWins)).toFixed(2)) : 0.5,
          status: 'completed',
        };
      }
    }
  });
});
