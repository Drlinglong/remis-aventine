import React from 'react';
import { Shield, Layers, Scale } from 'lucide-react';

export const MethodologyView: React.FC = () => {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '32px', marginBottom: '40px', maxWidth: '1000px', margin: '0 auto 40px' }}>
      {/* Hero Header */}
      <div>
        <span className="badge badge-gold" style={{ marginBottom: '8px' }}>EVALUATION GROUND MANIFESTO</span>
        <h1 style={{ fontSize: '28px', fontWeight: 800, color: 'var(--text-primary)', marginBottom: '10px' }}>
          Aventine Evaluation Methodology & Principles
        </h1>
        <p style={{ fontSize: '14px', color: 'var(--text-secondary)', lineHeight: 1.6 }}>
          Aventine evaluates complete translation pipelines (recipes), not isolated model names. A recipe includes provider, model revision, prompts, decoding settings, context, glossary handling, post-processing, repair, and optional deterministic validators.
        </p>
      </div>

      {/* The 4 Hard Principles */}
      <div className="av-card" style={{ padding: '24px', backgroundColor: 'var(--bg-card)' }}>
        <h2 style={{ fontSize: '18px', fontWeight: 800, color: 'var(--text-primary)', marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Shield size={20} color="var(--brand-gold)" /> The Four Hard Principles
        </h2>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '16px' }}>
          <div style={{ padding: '16px', backgroundColor: 'var(--bg-card-elevated)', borderRadius: 'var(--radius-md)' }}>
            <div style={{ fontSize: '14px', fontWeight: 700, color: 'var(--brand-gold)', marginBottom: '6px' }}>
              1. Hard Validators Have Veto Power
            </div>
            <p style={{ fontSize: '12px', color: 'var(--text-secondary)', lineHeight: 1.5 }}>
              An LLM judge cannot rescue a structurally unsafe output. If a candidate breaks placeholders, colour tags (<code>§Y...§!</code>), or YAML structure, it cannot defeat a valid output.
            </p>
          </div>

          <div style={{ padding: '16px', backgroundColor: 'var(--bg-card-elevated)', borderRadius: 'var(--radius-md)' }}>
            <div style={{ fontSize: '14px', fontWeight: 700, color: 'var(--brand-blue)', marginBottom: '6px' }}>
              2. The Judge Evaluates Soft Quality
            </div>
            <p style={{ fontSize: '12px', color: 'var(--text-secondary)', lineHeight: 1.5 }}>
              Semantics, terminology disambiguation, fluency, style, register, and repair over-editing belong to the calibrated judge.
            </p>
          </div>

          <div style={{ padding: '16px', backgroundColor: 'var(--bg-card-elevated)', borderRadius: 'var(--radius-md)' }}>
            <div style={{ fontSize: '14px', fontWeight: 700, color: 'var(--brand-emerald)', marginBottom: '6px' }}>
              3. Judge Output is Structured Data
            </div>
            <p style={{ fontSize: '12px', color: 'var(--text-secondary)', lineHeight: 1.5 }}>
              Parse failures and non-JSON responses are recorded as benchmark failures, never guessed at in prose.
            </p>
          </div>

          <div style={{ padding: '16px', backgroundColor: 'var(--bg-card-elevated)', borderRadius: 'var(--radius-md)' }}>
            <div style={{ fontSize: '14px', fontWeight: 700, color: 'var(--brand-purple)', marginBottom: '6px' }}>
              4. External Datasets Stay External
            </div>
            <p style={{ fontSize: '12px', color: 'var(--text-secondary)', lineHeight: 1.5 }}>
              Large WMT/ACES downloads and raw logs do not enter Git. Everything is validated against cryptographic SHA-256 contracts.
            </p>
          </div>
        </div>
      </div>

      {/* Issue #6 Capability Formulation */}
      <div className="av-card" style={{ padding: '24px', backgroundColor: 'var(--bg-card)' }}>
        <h2 style={{ fontSize: '18px', fontWeight: 800, color: 'var(--text-primary)', marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Layers size={20} color="var(--brand-blue)" /> Issue #6 Frontier Score Capability Tracks
        </h2>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '12px' }}>
          <div style={{ padding: '12px', backgroundColor: 'var(--bg-card-elevated)', borderRadius: 'var(--radius-md)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
              <strong style={{ fontSize: '13px', color: 'var(--text-primary)' }}>Semantic Fidelity</strong>
              <span className="badge badge-gold">30% Weight</span>
            </div>
            <p style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
              L1–L5 difficulty semantic traps, negation inversion, quantity alteration, entity substitution, omission, and discourse consistency.
            </p>
          </div>

          <div style={{ padding: '12px', backgroundColor: 'var(--bg-card-elevated)', borderRadius: 'var(--radius-md)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
              <strong style={{ fontSize: '13px', color: 'var(--text-primary)' }}>Constraint Integrity</strong>
              <span className="badge badge-emerald">20% Weight</span>
            </div>
            <p style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
              Placeholder tokens, variable parity, color tags (<code>§Y...§!</code>), escaped newlines, and glossary compliance.
            </p>
          </div>

          <div style={{ padding: '12px', backgroundColor: 'var(--bg-card-elevated)', borderRadius: 'var(--radius-md)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
              <strong style={{ fontSize: '13px', color: 'var(--text-primary)' }}>Cross-Context Consistency</strong>
              <span className="badge badge-blue">15% Weight</span>
            </div>
            <p style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
              Batch cohesion, pronoun/character voice alignment, and mitigating cross-batch drift under fixed context budgets.
            </p>
          </div>

          <div style={{ padding: '12px', backgroundColor: 'var(--bg-card-elevated)', borderRadius: 'var(--radius-md)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
              <strong style={{ fontSize: '13px', color: 'var(--text-primary)' }}>Repair Precision & Restraint</strong>
              <span className="badge badge-purple">15% Weight</span>
            </div>
            <p style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
              Fixing injected structural errors without damaging correct items or rewriting unnecessary text (over-editing control).
            </p>
          </div>

          <div style={{ padding: '12px', backgroundColor: 'var(--bg-card-elevated)', borderRadius: 'var(--radius-md)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
              <strong style={{ fontSize: '13px', color: 'var(--text-primary)' }}>Style & Voice</strong>
              <span className="badge badge-neutral">10% Weight</span>
            </div>
            <p style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
              Game lore immersion, character persona register, naturalness, and tone fidelity.
            </p>
          </div>

          <div style={{ padding: '12px', backgroundColor: 'var(--bg-card-elevated)', borderRadius: 'var(--radius-md)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
              <strong style={{ fontSize: '13px', color: 'var(--text-primary)' }}>Repeatability</strong>
              <span className="badge badge-neutral">10% Weight</span>
            </div>
            <p style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
              Consistency across 3–5 repeated runs, measuring output variance and provider rate-limit stability.
            </p>
          </div>
        </div>
      </div>

      {/* Stage Failure Multipliers */}
      <div className="av-card" style={{ padding: '24px', backgroundColor: 'var(--bg-card)' }}>
        <h2 style={{ fontSize: '18px', fontWeight: 800, color: 'var(--text-primary)', marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Scale size={20} color="var(--brand-emerald)" /> Stage-Specific Failure Multipliers
        </h2>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '16px' }}>
          <div style={{ padding: '16px', backgroundColor: 'var(--bg-card-elevated)', borderRadius: 'var(--radius-md)' }}>
            <h4 style={{ fontSize: '14px', fontWeight: 700, color: 'var(--text-primary)', marginBottom: '8px' }}>
              Translation Stage Policy
            </h4>
            <ul style={{ listStyle: 'none', display: 'flex', flexDirection: 'column', gap: '6px', fontSize: '12px' }}>
              <li style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span>Pass (Clean Execution)</span>
                <span className="mono" style={{ color: 'var(--brand-emerald)', fontWeight: 700 }}>× 1.00</span>
              </li>
              <li style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span>Recoverable hard/contract issue</span>
                <span className="mono" style={{ color: 'var(--brand-gold)', fontWeight: 700 }}>× 0.67</span>
              </li>
              <li style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span>Unusable / misaligned / empty</span>
                <span className="mono" style={{ color: 'var(--brand-rose)', fontWeight: 700 }}>× 0.00</span>
              </li>
              <li style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span>Execution / API failure</span>
                <span className="mono" style={{ color: 'var(--brand-rose)', fontWeight: 700 }}>× 0.00</span>
              </li>
            </ul>
          </div>

          <div style={{ padding: '16px', backgroundColor: 'var(--bg-card-elevated)', borderRadius: 'var(--radius-md)' }}>
            <h4 style={{ fontSize: '14px', fontWeight: 700, color: 'var(--text-primary)', marginBottom: '8px' }}>
              Proofreading & Repair Stage Policy
            </h4>
            <ul style={{ listStyle: 'none', display: 'flex', flexDirection: 'column', gap: '6px', fontSize: '12px' }}>
              <li style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span>Pass (Restrained Repair)</span>
                <span className="mono" style={{ color: 'var(--brand-emerald)', fontWeight: 700 }}>× 1.00</span>
              </li>
              <li style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span>Damaging valid items</span>
                <span className="mono" style={{ color: 'var(--brand-rose)', fontWeight: 700 }}>× 0.00</span>
              </li>
              <li style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span>Any hard / format failure</span>
                <span className="mono" style={{ color: 'var(--brand-rose)', fontWeight: 700 }}>× 0.00</span>
              </li>
              <li style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span>Execution failure</span>
                <span className="mono" style={{ color: 'var(--brand-rose)', fontWeight: 700 }}>× 0.00</span>
              </li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
};
