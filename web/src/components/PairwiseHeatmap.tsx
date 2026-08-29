import React, { useState } from 'react';
import { Swords, X } from 'lucide-react';
import { PILOT_MODEL_IDS, PAIRWISE_MATRIX_DATA } from '../data/pairwiseData';
import { BENCHMARK_RECIPES } from '../data/benchmarkData';
import type { PairwiseCell, RecipeEntry } from '../types/benchmark';

interface PairwiseHeatmapProps {
  onSelectModel: (recipe: RecipeEntry) => void;
}

export const PairwiseHeatmap: React.FC<PairwiseHeatmapProps> = ({ onSelectModel: _onSelectModel }) => {
  const [selectedCell, setSelectedCell] = useState<PairwiseCell | null>(null);

  const getModel = (id: string) => BENCHMARK_RECIPES.find((r) => r.id === id) || BENCHMARK_RECIPES[0];

  const getCellColor = (cell: PairwiseCell) => {
    if (cell.status === 'self') return 'var(--bg-card-elevated)';
    if (cell.left_wins > cell.right_wins) {
      const intensity = Math.min(0.35, 0.1 + (cell.left_wins - cell.right_wins) * 0.05);
      return `rgba(16, 185, 129, ${intensity})`;
    } else if (cell.left_wins < cell.right_wins) {
      const intensity = Math.min(0.35, 0.1 + (cell.right_wins - cell.left_wins) * 0.05);
      return `rgba(244, 63, 94, ${intensity})`;
    } else {
      return 'rgba(229, 169, 60, 0.15)';
    }
  };

  return (
    <div className="av-card" style={{ padding: '24px', backgroundColor: 'var(--bg-card)', marginBottom: '32px' }}>
      {/* Header */}
      <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', justifyContent: 'space-between', gap: '16px', marginBottom: '20px' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <h2 style={{ fontSize: '18px', fontWeight: 800, color: 'var(--text-primary)' }}>
              9x9 Head-to-Head Round-Robin Arena
            </h2>
            <span className="badge badge-gold">36 Pairwise Matchups</span>
          </div>
          <p style={{ fontSize: '12px', color: 'var(--text-secondary)', marginTop: '2px' }}>
            Position-swapped blind judgments evaluated by DeepSeek V4 Flash. Click any cell to inspect case verdicts.
          </p>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', fontSize: '11px', color: 'var(--text-secondary)' }}>
          <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
            <span style={{ width: '10px', height: '10px', backgroundColor: 'rgba(16, 185, 129, 0.35)', borderRadius: '2px' }} /> Row Wins
          </span>
          <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
            <span style={{ width: '10px', height: '10px', backgroundColor: 'rgba(229, 169, 60, 0.35)', borderRadius: '2px' }} /> Tie / Even
          </span>
          <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
            <span style={{ width: '10px', height: '10px', backgroundColor: 'rgba(244, 63, 94, 0.35)', borderRadius: '2px' }} /> Row Loses
          </span>
        </div>
      </div>

      {/* Grid Table */}
      <div style={{ overflowX: 'auto', paddingBottom: '8px' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '11px', textAlign: 'center' }}>
          <thead>
            <tr>
              <th style={{ textAlign: 'left', padding: '10px', color: 'var(--text-muted)', minWidth: '150px' }}>
                Row vs. Col
              </th>
              {PILOT_MODEL_IDS.map((colId, index) => {
                const model = getModel(colId);
                return (
                  <th
                    key={colId}
                    style={{ padding: '8px 4px', color: 'var(--text-secondary)', minWidth: '55px' }}
                    title={model.label}
                  >
                    <div>#{index + 1}</div>
                    <div style={{ fontSize: '9px', color: 'var(--text-muted)', fontWeight: 400 }}>
                      {model.label.split(' ')[0]}
                    </div>
                  </th>
                );
              })}
            </tr>
          </thead>
          <tbody>
            {PILOT_MODEL_IDS.map((rowId, rowIndex) => {
              const rowModel = getModel(rowId);
              return (
                <tr key={rowId} style={{ borderTop: '1px solid var(--border-subtle)' }}>
                  {/* Row Model Header */}
                  <td style={{ textAlign: 'left', padding: '8px 10px' }}>
                    <div style={{ fontWeight: 700, color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: '6px' }}>
                      <span className="badge badge-neutral" style={{ fontSize: '9px', padding: '0 4px' }}>#{rowIndex + 1}</span>
                      <span style={{ whiteSpace: 'nowrap' }}>{rowModel.label.split('(')[0]}</span>
                    </div>
                  </td>

                  {/* Matrix Cells */}
                  {PILOT_MODEL_IDS.map((colId) => {
                    const cell = PAIRWISE_MATRIX_DATA[rowId]?.[colId] || {
                      left_id: rowId,
                      right_id: colId,
                      left_wins: 0,
                      right_wins: 0,
                      ties: 0,
                      unresolved: 0,
                      total_cases: 7,
                      win_rate: 0.5,
                      status: 'self',
                    };

                    const isSelf = cell.status === 'self';
                    const isSelected =
                      selectedCell &&
                      selectedCell.left_id === cell.left_id &&
                      selectedCell.right_id === cell.right_id;

                    return (
                      <td key={colId} style={{ padding: '4px' }}>
                        <div
                          onClick={() => !isSelf && setSelectedCell(cell)}
                          style={{
                            backgroundColor: getCellColor(cell),
                            borderRadius: 'var(--radius-sm)',
                            padding: '6px 2px',
                            cursor: isSelf ? 'default' : 'pointer',
                            border: isSelected
                              ? '1.5px solid var(--brand-gold)'
                              : isSelf
                              ? '1px solid transparent'
                              : '1px solid var(--border-subtle)',
                            transition: 'transform 0.15s ease, border-color 0.15s ease',
                          }}
                          className="mono"
                        >
                          {isSelf ? (
                            <span style={{ color: 'var(--text-muted)' }}>-</span>
                          ) : (
                            <div style={{ fontWeight: 700, color: 'var(--text-primary)' }}>
                              {cell.left_wins}-{cell.right_wins}
                            </div>
                          )}
                        </div>
                      </td>
                    );
                  })}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Selected Matchup Detail Box */}
      {selectedCell && selectedCell.status !== 'self' && (
        <div
          className="animate-fade-in"
          style={{
            marginTop: '20px',
            padding: '20px',
            backgroundColor: 'var(--bg-card-elevated)',
            borderRadius: 'var(--radius-lg)',
            border: '1px solid var(--border-medium)',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
              <Swords size={20} color="var(--brand-gold)" />
              <h3 style={{ fontSize: '16px', fontWeight: 800, color: 'var(--text-primary)' }}>
                {getModel(selectedCell.left_id).label} vs. {getModel(selectedCell.right_id).label}
              </h3>
            </div>
            <button onClick={() => setSelectedCell(null)} style={{ color: 'var(--text-muted)' }}>
              <X size={16} />
            </button>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '12px', marginBottom: '16px' }}>
            <div style={{ padding: '12px', backgroundColor: 'var(--bg-card)', borderRadius: 'var(--radius-md)', textAlign: 'center' }}>
              <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Left Model Wins</div>
              <div className="mono" style={{ fontSize: '20px', fontWeight: 800, color: 'var(--brand-emerald)' }}>
                {selectedCell.left_wins}
              </div>
            </div>
            <div style={{ padding: '12px', backgroundColor: 'var(--bg-card)', borderRadius: 'var(--radius-md)', textAlign: 'center' }}>
              <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Right Model Wins</div>
              <div className="mono" style={{ fontSize: '20px', fontWeight: 800, color: 'var(--brand-rose)' }}>
                {selectedCell.right_wins}
              </div>
            </div>
            <div style={{ padding: '12px', backgroundColor: 'var(--bg-card)', borderRadius: 'var(--radius-md)', textAlign: 'center' }}>
              <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Ties / Equal</div>
              <div className="mono" style={{ fontSize: '20px', fontWeight: 800, color: 'var(--brand-gold)' }}>
                {selectedCell.ties}
              </div>
            </div>
            <div style={{ padding: '12px', backgroundColor: 'var(--bg-card)', borderRadius: 'var(--radius-md)', textAlign: 'center' }}>
              <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Unresolved (Swap Disagreement)</div>
              <div className="mono" style={{ fontSize: '20px', fontWeight: 800, color: 'var(--text-secondary)' }}>
                {selectedCell.unresolved}
              </div>
            </div>
          </div>

          {/* Sample cases if available */}
          {selectedCell.cases && selectedCell.cases.length > 0 && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              <div style={{ fontSize: '12px', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase' }}>
                Sample Blind Judgments & Swap Verification
              </div>
              {selectedCell.cases.map((c) => (
                <div key={c.case_id} style={{ backgroundColor: 'var(--bg-card)', padding: '14px', borderRadius: 'var(--radius-md)' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
                    <span style={{ fontWeight: 700, color: 'var(--text-primary)', fontSize: '13px' }}>{c.title}</span>
                    <span className={`badge ${c.verdict === 'left_win' ? 'badge-emerald' : 'badge-neutral'}`}>
                      {c.verdict.toUpperCase().replace('_', ' ')}
                    </span>
                  </div>
                  <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginBottom: '6px' }}>
                    <strong>Source:</strong> <code>{c.source_text}</code>
                  </div>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px', fontSize: '12px', marginBottom: '8px' }}>
                    <div style={{ padding: '8px', backgroundColor: 'var(--bg-input)', borderRadius: 'var(--radius-sm)' }}>
                      <strong>Candidate A (Left):</strong> {c.candidate_a}
                    </div>
                    <div style={{ padding: '8px', backgroundColor: 'var(--bg-input)', borderRadius: 'var(--radius-sm)' }}>
                      <strong>Candidate B (Right):</strong> {c.candidate_b}
                    </div>
                  </div>
                  <div style={{ fontSize: '11px', color: 'var(--text-secondary)', borderTop: '1px solid var(--border-subtle)', paddingTop: '6px' }}>
                    <strong>Judge Rationale:</strong> {c.reason}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
};
