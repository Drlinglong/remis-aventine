import React from 'react';
import { ShieldCheck, FileText } from 'lucide-react';
import { CALIBRATION_DATA } from '../data/calibrationData';

export const CalibrationView: React.FC = () => {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '32px', marginBottom: '32px' }}>
      {/* Intro Banner */}
      <div
        className="av-card"
        style={{
          padding: '24px',
          background: 'linear-gradient(135deg, var(--bg-card) 0%, var(--bg-card-elevated) 100%)',
          border: '1px solid rgba(229, 169, 60, 0.3)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '8px' }}>
          <ShieldCheck size={24} color="var(--brand-gold)" />
          <h2 style={{ fontSize: '20px', fontWeight: 800, color: 'var(--text-primary)' }}>
            Rule #4: Calibrate the Judge, Never Blindly Trust It
          </h2>
        </div>
        <p style={{ fontSize: '13px', color: 'var(--text-secondary)', lineHeight: 1.6, maxWidth: '900px' }}>
          LLM judgments are never human gold labels. In Aventine, judges (DeepSeek V4 Flash, Gemini 3.7) are rigorously calibrated against professional human MQM error annotations, ACES contrastive challenge sets, and independent neural baselines (MetricX-24, xCOMET).
        </p>
      </div>

      {/* Calibration Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(360px, 1fr))', gap: '24px' }}>
        {CALIBRATION_DATA.map((item) => (
          <div key={item.id} className="av-card" style={{ padding: '24px', backgroundColor: 'var(--bg-card)' }}>
            <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: '16px' }}>
              <div>
                <span className="badge badge-gold" style={{ fontSize: '10px', marginBottom: '6px' }}>
                  {item.type.toUpperCase()} BENCHMARK
                </span>
                <h3 style={{ fontSize: '16px', fontWeight: 800, color: 'var(--text-primary)' }}>{item.name}</h3>
                <p style={{ fontSize: '12px', color: 'var(--text-muted)' }}>{item.target_measure}</p>
              </div>
            </div>

            {/* Metrics KPI row */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '8px', marginBottom: '20px' }}>
              <div style={{ padding: '10px', backgroundColor: 'var(--bg-card-elevated)', borderRadius: 'var(--radius-md)', textAlign: 'center' }}>
                <div style={{ fontSize: '10px', color: 'var(--text-muted)' }}>Severe Recall</div>
                <div className="mono" style={{ fontSize: '18px', fontWeight: 800, color: 'var(--brand-emerald)' }}>
                  {item.severe_error_recall}%
                </div>
              </div>
              <div style={{ padding: '10px', backgroundColor: 'var(--bg-card-elevated)', borderRadius: 'var(--radius-md)', textAlign: 'center' }}>
                <div style={{ fontSize: '10px', color: 'var(--text-muted)' }}>False-Good Rate</div>
                <div className="mono" style={{ fontSize: '18px', fontWeight: 800, color: 'var(--brand-gold)' }}>
                  {item.false_good_rate}%
                </div>
              </div>
              <div style={{ padding: '10px', backgroundColor: 'var(--bg-card-elevated)', borderRadius: 'var(--radius-md)', textAlign: 'center' }}>
                <div style={{ fontSize: '10px', color: 'var(--text-muted)' }}>Judge Accuracy</div>
                <div className="mono" style={{ fontSize: '18px', fontWeight: 800, color: 'var(--brand-blue)' }}>
                  {item.judge_accuracy}%
                </div>
              </div>
            </div>

            {/* Phenomena breakdown */}
            <div style={{ fontSize: '12px', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '10px' }}>
              Phenomenon Error Diagnostic
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', marginBottom: '16px' }}>
              {item.phenomena_breakdown.map((p) => (
                <div key={p.name} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: '12px' }}>
                  <span style={{ color: 'var(--text-secondary)' }}>{p.name}</span>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <div style={{ width: '80px', height: '5px', backgroundColor: 'var(--bg-muted)', borderRadius: '3px', overflow: 'hidden' }}>
                      <div style={{ width: `${p.judge_accuracy}%`, height: '100%', backgroundColor: 'var(--brand-emerald)' }} />
                    </div>
                    <span className="mono" style={{ color: 'var(--text-primary)', fontWeight: 600 }}>{p.judge_accuracy}%</span>
                  </div>
                </div>
              ))}
            </div>

            {/* Provenance footer */}
            <div style={{ borderTop: '1px solid var(--border-subtle)', paddingTop: '12px', fontSize: '11px', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: '4px' }}>
              <FileText size={12} />
              <span>{item.provenance}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
