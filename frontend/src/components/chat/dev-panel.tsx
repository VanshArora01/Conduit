'use client';

import { useState, useRef, useCallback, useEffect } from 'react';
import {
  X, ChevronUp, ChevronDown, Activity, Brain, ListChecks, Wrench,
  Search, FileText, Coins, Timer, ScrollText, AlertTriangle,
  GripHorizontal, Maximize2, Minimize2
} from 'lucide-react';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface DevPanelProps {
  debugMetadata: any;
  isOpen: boolean;
  onClose: () => void;
}

type TabId =
  | 'overview'
  | 'planner'
  | 'execution'
  | 'tools'
  | 'retrieval'
  | 'chunks'
  | 'prompt'
  | 'tokens'
  | 'latency'
  | 'timeline'
  | 'logs'
  | 'errors';

interface TabDef {
  id: TabId;
  label: string;
  icon: React.ReactNode;
}

const TABS: TabDef[] = [
  { id: 'overview', label: 'Overview', icon: <Activity size={13} /> },
  { id: 'planner', label: 'Planner', icon: <Brain size={13} /> },
  { id: 'execution', label: 'Execution Plan', icon: <ListChecks size={13} /> },
  { id: 'tools', label: 'Tools', icon: <Wrench size={13} /> },
  { id: 'retrieval', label: 'Retrieval', icon: <Search size={13} /> },
  { id: 'chunks', label: 'Chunks', icon: <FileText size={13} /> },
  { id: 'prompt', label: 'Prompt', icon: <FileText size={13} /> },
  { id: 'tokens', label: 'Tokens', icon: <Coins size={13} /> },
  { id: 'latency', label: 'Latency', icon: <Timer size={13} /> },
  { id: 'timeline', label: 'Timeline', icon: <Activity size={13} /> },
  { id: 'logs', label: 'Logs', icon: <ScrollText size={13} /> },
  { id: 'errors', label: 'Errors', icon: <AlertTriangle size={13} /> },
];

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function JsonBlock({ data, label }: { data: any; label?: string }) {
  if (data === undefined || data === null) {
    return <span className="text-[var(--muted-fg)] italic text-[11px]">No data</span>;
  }
  return (
    <div className="relative">
      {label && <div className="text-[10px] uppercase font-bold tracking-wider text-[var(--muted-fg)] mb-1.5">{label}</div>}
      <pre className="text-[11px] leading-[1.5] font-mono text-[var(--foreground)] bg-[var(--background)] border border-[var(--border)] rounded-md p-3 overflow-x-auto whitespace-pre-wrap break-all max-h-[300px] overflow-y-auto">
        {typeof data === 'string' ? data : JSON.stringify(data, null, 2)}
      </pre>
    </div>
  );
}

function MetricCard({ label, value, unit, color }: { label: string; value: string | number; unit?: string; color?: string }) {
  return (
    <div className="flex flex-col gap-0.5 p-2.5 bg-[var(--background)] border border-[var(--border)] rounded-lg min-w-[110px]">
      <span className="text-[9px] uppercase font-bold tracking-widest text-[var(--muted-fg)]">{label}</span>
      <span className={`text-sm font-mono font-semibold ${color || 'text-[var(--foreground)]'}`}>
        {value}{unit && <span className="text-[10px] text-[var(--muted-fg)] ml-0.5">{unit}</span>}
      </span>
    </div>
  );
}

function StatusBadge({ success }: { success: boolean }) {
  return (
    <span className={`inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider ${success ? 'bg-[var(--success)]/15 text-[var(--success)]' : 'bg-[var(--danger)]/15 text-[var(--danger)]'}`}>
      {success ? 'OK' : 'FAIL'}
    </span>
  );
}

// ---------------------------------------------------------------------------
// Tab Panes
// ---------------------------------------------------------------------------

function OverviewPane({ d }: { d: any }) {
  const plan = d?.plan || {};
  const metrics = d?.executor_metrics || {};
  return (
    <div className="flex flex-col gap-4">
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-2">
        <MetricCard label="Task" value={plan.task || 'N/A'} />
        <MetricCard label="Confidence" value={plan.confidence != null ? `${(plan.confidence * 100).toFixed(0)}%` : 'N/A'} />
        <MetricCard label="Steps" value={metrics.steps_executed || 0} />
        <MetricCard label="Failed" value={metrics.steps_failed || 0} color={metrics.steps_failed > 0 ? 'text-[var(--danger)]' : undefined} />
        <MetricCard label="Total Time" value={d?.total_time_ms || metrics.total_latency_ms || 0} unit="ms" />
        <MetricCard label="Cost" value={`$${(d?.cost || metrics.estimated_cost_usd || 0).toFixed(6)}`} color="text-[var(--success)]" />
      </div>
      {plan.reasoning && (
        <div>
          <div className="text-[10px] uppercase font-bold tracking-wider text-[var(--muted-fg)] mb-1">Reasoning</div>
          <div className="text-xs text-[var(--foreground)] bg-[var(--background)] border border-[var(--border)] rounded-md p-3 italic">
            {plan.reasoning}
          </div>
        </div>
      )}
      {d?.pipeline_id && (
        <div className="flex flex-wrap gap-2 text-[10px] font-mono text-[var(--muted-fg)]">
          {d.pipeline_id && <span>Pipeline: {d.pipeline_id}</span>}
          {d.request_id && <span>• Req: {d.request_id}</span>}
          {d.conversation_id && <span>• Conv: {d.conversation_id}</span>}
        </div>
      )}
    </div>
  );
}

function PlannerPane({ d }: { d: any }) {
  const plan = d?.plan || {};
  return (
    <div className="flex flex-col gap-4">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
        <MetricCard label="Task Type" value={plan.task || 'N/A'} />
        <MetricCard label="Confidence" value={plan.confidence != null ? `${(plan.confidence * 100).toFixed(0)}%` : 'N/A'} />
        <MetricCard label="Fallback?" value={plan.is_fallback ? 'YES' : 'NO'} color={plan.is_fallback ? 'text-[var(--warning)]' : undefined} />
        <MetricCard label="Planner Time" value={d?.planner_time_ms || 0} unit="ms" />
      </div>
      {plan.steps && (
        <div>
          <div className="text-[10px] uppercase font-bold tracking-wider text-[var(--muted-fg)] mb-1.5">Planned Steps</div>
          <div className="flex flex-wrap gap-1.5">
            {plan.steps.map((step: string, i: number) => (
              <span key={i} className="px-2 py-1 bg-[var(--surface-active)] border border-[var(--border)] rounded text-[11px] font-mono text-[var(--foreground)]">
                {i + 1}. {step}
              </span>
            ))}
          </div>
        </div>
      )}
      {plan.reasoning && (
        <div>
          <div className="text-[10px] uppercase font-bold tracking-wider text-[var(--muted-fg)] mb-1">Reasoning</div>
          <div className="text-xs text-[var(--foreground)] bg-[var(--background)] border border-[var(--border)] rounded-md p-3 italic">
            {plan.reasoning}
          </div>
        </div>
      )}
      {plan.fallback_reason && (
        <div>
          <div className="text-[10px] uppercase font-bold tracking-wider text-[var(--warning)] mb-1">Fallback Reason</div>
          <div className="text-xs text-[var(--foreground)] bg-[var(--background)] border border-[var(--danger)]/30 rounded-md p-3">
            {plan.fallback_reason}
          </div>
        </div>
      )}
      <JsonBlock data={d?.execution_plan} label="Full Execution Plan (JSON)" />
    </div>
  );
}

function ExecutionPane({ d }: { d: any }) {
  const toolGraph = d?.tool_graph || [];
  return (
    <div className="flex flex-col gap-4">
      <div className="text-[10px] uppercase font-bold tracking-wider text-[var(--muted-fg)] mb-1">Execution Graph ({toolGraph.length} steps)</div>
      {toolGraph.length === 0 ? (
        <span className="text-[var(--muted-fg)] italic text-xs">No steps executed.</span>
      ) : (
        <div className="flex flex-col gap-1.5">
          {toolGraph.map((step: any, i: number) => (
            <div key={i} className="flex items-center gap-3 p-2.5 bg-[var(--background)] border border-[var(--border)] rounded-lg text-xs font-mono">
              <span className="w-5 text-center text-[var(--muted-fg)]">{i + 1}</span>
              <span className="flex-1 text-[var(--foreground)] font-medium">{step.tool}</span>
              <StatusBadge success={step.success} />
              <span className="text-[var(--muted-fg)] text-[11px] min-w-[60px] text-right">{step.latency_ms || 0}ms</span>
              {step.retried && <span className="text-[var(--warning)] text-[10px]">RETRY</span>}
              {step.error && <span className="text-[var(--danger)] text-[10px] truncate max-w-[200px]" title={step.error}>{step.error}</span>}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function ToolsPane({ d }: { d: any }) {
  const toolGraph = d?.tool_graph || [];
  const metrics = d?.executor_metrics || {};
  return (
    <div className="flex flex-col gap-4">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
        <MetricCard label="Tools Run" value={metrics.steps_executed || toolGraph.length} />
        <MetricCard label="Failed" value={metrics.steps_failed || 0} color={metrics.steps_failed > 0 ? 'text-[var(--danger)]' : undefined} />
        <MetricCard label="Retries" value={metrics.retries || 0} color={metrics.retries > 0 ? 'text-[var(--warning)]' : undefined} />
        <MetricCard label="Tool Latency" value={metrics.total_tool_latency_ms || 0} unit="ms" />
      </div>
      {toolGraph.length > 0 && (
        <div className="flex flex-col gap-3">
          {toolGraph.map((step: any, i: number) => (
            <div key={i} className="p-3 bg-[var(--background)] border border-[var(--border)] rounded-lg">
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-mono font-semibold text-[var(--foreground)]">{step.tool}</span>
                <StatusBadge success={step.success} />
              </div>
              <div className="grid grid-cols-3 gap-2 text-[10px]">
                <div><span className="text-[var(--muted-fg)]">Step ID:</span> <span className="font-mono">{step.step_id}</span></div>
                <div><span className="text-[var(--muted-fg)]">Latency:</span> <span className="font-mono">{step.latency_ms || 0}ms</span></div>
                <div><span className="text-[var(--muted-fg)]">Retried:</span> <span className="font-mono">{step.retried ? 'YES' : 'NO'}</span></div>
              </div>
              {step.error && (
                <div className="mt-2 text-[10px] text-[var(--danger)] bg-[var(--danger)]/5 rounded p-2 font-mono break-all">
                  {step.error}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function RetrievalPane({ d }: { d: any }) {
  const retrieval = d?.retrieval || {};
  return (
    <div className="flex flex-col gap-4">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
        <MetricCard label="Chunks Retrieved" value={retrieval.chunks_retrieved || 0} />
        <MetricCard label="Chunks Selected" value={retrieval.selected_chunks_count || 0} />
        <MetricCard label="Threshold" value={retrieval.similarity_threshold || 'N/A'} />
        <MetricCard label="Documents" value={(retrieval.document_ids || []).filter(Boolean).length} />
      </div>
      {retrieval.scores && retrieval.scores.length > 0 && (
        <div>
          <div className="text-[10px] uppercase font-bold tracking-wider text-[var(--muted-fg)] mb-1.5">Similarity Scores</div>
          <div className="flex flex-wrap gap-1.5">
            {retrieval.scores.map((score: number, i: number) => (
              <span key={i} className={`px-2 py-0.5 rounded text-[10px] font-mono border ${score >= 0.75 ? 'bg-[var(--success)]/10 border-[var(--success)]/30 text-[var(--success)]' : score >= 0.55 ? 'bg-[var(--warning)]/10 border-[var(--warning)]/30 text-[var(--warning)]' : score >= 0.35 ? 'bg-[var(--accent)]/10 border-[var(--accent)]/30 text-[var(--accent)]' : 'bg-[var(--danger)]/10 border-[var(--danger)]/30 text-[var(--danger)]'}`}>
                {score.toFixed(4)}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function ChunksPane({ d }: { d: any }) {
  const records = d?.retrieval?.records || [];
  return (
    <div className="flex flex-col gap-4">
      <div className="text-[10px] uppercase font-bold tracking-wider text-[var(--muted-fg)] mb-1.5">Chunk Selection Decision Log</div>
      {records.length === 0 ? (
        <span className="text-[var(--muted-fg)] italic text-xs">No chunks retrieved.</span>
      ) : (
        <div className="flex flex-col gap-2">
          {records.map((r: any, i: number) => (
            <div key={i} className={`p-3 border rounded-lg ${r.selected ? 'bg-[var(--success)]/5 border-[var(--success)]/20' : 'bg-[var(--background)] border-[var(--border)]'}`}>
              <div className="flex justify-between items-center mb-2">
                <span className="text-xs font-semibold">{r.document_title}</span>
                <span className={`text-[10px] px-2 py-0.5 rounded font-mono ${r.selected ? 'bg-[var(--success)]/10 text-[var(--success)]' : 'bg-[var(--surface-active)] text-[var(--muted-fg)]'}`}>
                  {r.band || 'Unknown'} Band
                </span>
              </div>
              <div className="grid grid-cols-2 gap-2 text-[10px]">
                <div><span className="text-[var(--muted-fg)]">Score:</span> <span className="font-mono">{r.score?.toFixed(4)}</span></div>
                <div><span className="text-[var(--muted-fg)]">Status:</span> <span className="font-mono">{r.selected ? 'SELECTED' : 'DROPPED'}</span></div>
              </div>
              <div className="mt-2 text-[10px] text-[var(--muted-fg)] italic">Reason: {r.reason}</div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function PromptPane({ d }: { d: any }) {
  const prompt = d?.built_prompt || d?.execution_plan?.built_prompt;
  return (
    <div className="flex flex-col gap-4">
      {prompt ? (
        <div>
          <div className="text-[10px] uppercase font-bold tracking-wider text-[var(--muted-fg)] mb-1.5">Built Prompt</div>
          <pre className="text-[11px] leading-[1.6] font-mono text-[var(--foreground)] bg-[var(--background)] border border-[var(--border)] rounded-md p-4 overflow-x-auto whitespace-pre-wrap break-words max-h-[500px] overflow-y-auto">
            {prompt}
          </pre>
        </div>
      ) : (
        <span className="text-[var(--muted-fg)] italic text-xs">Prompt not captured. Enable DEBUG_AI in backend config.</span>
      )}
    </div>
  );
}

function TokensPane({ d }: { d: any }) {
  const metrics = d?.executor_metrics || {};
  const promptTokens = d?.prompt_tokens || metrics.prompt_tokens || 0;
  const completionTokens = d?.completion_tokens || metrics.completion_tokens || 0;
  const totalTokens = promptTokens + completionTokens;
  const cost = d?.cost || metrics.estimated_cost_usd || 0;
  const budget = 3000;
  const budgetPct = Math.min(100, Math.round((promptTokens / budget) * 100));
  return (
    <div className="flex flex-col gap-4">
      <div className="text-[10px] uppercase font-bold tracking-wider text-[var(--muted-fg)]">Token & Cost Dashboard</div>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
        <MetricCard label="Prompt Tokens" value={promptTokens} />
        <MetricCard label="Completion Tokens" value={completionTokens} />
        <MetricCard label="Total Tokens" value={totalTokens} />
        <MetricCard label="Est. Cost" value={`$${cost.toFixed(6)}`} color="text-[var(--success)]" />
      </div>
      <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
        <MetricCard label="Context Budget" value={budget} unit="tok" />
        <MetricCard label="Budget Used" value={`${budgetPct}%`} color={budgetPct > 90 ? 'text-[var(--danger)]' : undefined} />
        <MetricCard label="Max Chunks" value={5} />
      </div>
      {totalTokens > 0 && (
        <div>
          <div className="text-[10px] uppercase font-bold tracking-wider text-[var(--muted-fg)] mb-2">Token Distribution</div>
          <div className="h-3 w-full bg-[var(--border)] rounded-full overflow-hidden flex">
            <div
              className="h-full bg-blue-500 transition-all"
              style={{ width: `${totalTokens > 0 ? (promptTokens / totalTokens) * 100 : 0}%` }}
              title={`Prompt: ${promptTokens}`}
            />
            <div
              className="h-full bg-emerald-500 transition-all"
              style={{ width: `${totalTokens > 0 ? (completionTokens / totalTokens) * 100 : 0}%` }}
              title={`Completion: ${completionTokens}`}
            />
          </div>
          <div className="flex justify-between mt-1 text-[10px] text-[var(--muted-fg)]">
            <span className="flex items-center gap-1"><span className="w-2 h-2 bg-blue-500 rounded-sm inline-block" /> Prompt ({promptTokens})</span>
            <span className="flex items-center gap-1"><span className="w-2 h-2 bg-emerald-500 rounded-sm inline-block" /> Completion ({completionTokens})</span>
          </div>
        </div>
      )}
    </div>
  );
}

function LatencyPane({ d }: { d: any }) {
  const metrics = d?.executor_metrics || {};
  const toolGraph = d?.tool_graph || [];
  const plannerMs = d?.planner_time_ms || metrics.planner_latency_ms || 0;
  const toolMs = metrics.total_tool_latency_ms || 0;
  const llmMs = metrics.llm_latency_ms || 0;
  const totalMs = d?.total_time_ms || metrics.total_latency_ms || 0;

  return (
    <div className="flex flex-col gap-4">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
        <MetricCard label="Planner" value={plannerMs} unit="ms" />
        <MetricCard label="Tools" value={toolMs} unit="ms" />
        <MetricCard label="LLM" value={llmMs} unit="ms" />
        <MetricCard label="Total" value={totalMs} unit="ms" color="text-[var(--foreground)]" />
      </div>
      {totalMs > 0 && (
        <div>
          <div className="text-[10px] uppercase font-bold tracking-wider text-[var(--muted-fg)] mb-2">Latency Breakdown</div>
          <div className="h-5 w-full bg-[var(--border)] rounded-full overflow-hidden flex">
            {plannerMs > 0 && (
              <div className="h-full bg-violet-500 transition-all flex items-center justify-center"
                style={{ width: `${(plannerMs / totalMs) * 100}%` }}
                title={`Planner: ${plannerMs}ms`}>
                {plannerMs / totalMs > 0.1 && <span className="text-[9px] text-white font-mono">{plannerMs}ms</span>}
              </div>
            )}
            {toolMs > 0 && (
              <div className="h-full bg-amber-500 transition-all flex items-center justify-center"
                style={{ width: `${(toolMs / totalMs) * 100}%` }}
                title={`Tools: ${toolMs}ms`}>
                {toolMs / totalMs > 0.1 && <span className="text-[9px] text-white font-mono">{toolMs}ms</span>}
              </div>
            )}
            {llmMs > 0 && (
              <div className="h-full bg-cyan-500 transition-all flex items-center justify-center"
                style={{ width: `${(llmMs / totalMs) * 100}%` }}
                title={`LLM: ${llmMs}ms`}>
                {llmMs / totalMs > 0.1 && <span className="text-[9px] text-white font-mono">{llmMs}ms</span>}
              </div>
            )}
          </div>
          <div className="flex flex-wrap gap-3 mt-1.5 text-[10px] text-[var(--muted-fg)]">
            <span className="flex items-center gap-1"><span className="w-2 h-2 bg-violet-500 rounded-sm" /> Planner</span>
            <span className="flex items-center gap-1"><span className="w-2 h-2 bg-amber-500 rounded-sm" /> Tools</span>
            <span className="flex items-center gap-1"><span className="w-2 h-2 bg-cyan-500 rounded-sm" /> LLM</span>
          </div>
        </div>
      )}
      {toolGraph.length > 0 && (
        <div>
          <div className="text-[10px] uppercase font-bold tracking-wider text-[var(--muted-fg)] mb-1.5">Per-Tool Latency</div>
          <div className="flex flex-col gap-1">
            {toolGraph.map((step: any, i: number) => (
              <div key={i} className="flex items-center gap-2 text-[11px] font-mono">
                <span className="text-[var(--muted-fg)] w-4 text-right">{i + 1}.</span>
                <span className="flex-1 text-[var(--foreground)]">{step.tool}</span>
                <div className="flex-1 h-2 bg-[var(--border)] rounded-full overflow-hidden">
                  <div className="h-full bg-amber-500/70 rounded-full" style={{ width: `${totalMs > 0 ? ((step.latency_ms || 0) / totalMs) * 100 : 0}%` }} />
                </div>
                <span className="text-[var(--muted-fg)] min-w-[50px] text-right">{step.latency_ms || 0}ms</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function TimelinePane({ d }: { d: any }) {
  const toolGraph = d?.tool_graph || [];
  const metrics = d?.executor_metrics || {};
  const plannerMs = d?.planner_time_ms || metrics.planner_latency_ms || 0;

  return (
    <div className="flex flex-col gap-4">
      <div className="text-[10px] uppercase font-bold tracking-wider text-[var(--muted-fg)] mb-1">Execution Timeline</div>
      <div className="flex flex-col gap-0 border-l-2 border-[var(--border)] ml-3 pl-4 relative">
        <div className="mb-4 relative">
          <div className="absolute -left-[23px] top-1 w-3 h-3 rounded-full bg-[var(--accent)] border-2 border-[var(--background)]"></div>
          <div className="text-xs font-semibold text-[var(--foreground)]">Planning</div>
          <div className="text-[10px] text-[var(--muted-fg)]">LLM routing and intent generation ({plannerMs}ms)</div>
        </div>
        {toolGraph.map((step: any, i: number) => (
          <div key={i} className="mb-4 relative">
            <div className={`absolute -left-[23px] top-1 w-3 h-3 rounded-full border-2 border-[var(--background)] ${step.success ? 'bg-[var(--success)]' : 'bg-[var(--danger)]'}`}></div>
            <div className="text-xs font-semibold text-[var(--foreground)]">Tool: {step.tool}</div>
            <div className="text-[10px] text-[var(--muted-fg)]">Execution time: {step.latency_ms || 0}ms</div>
          </div>
        ))}
        <div className="relative">
          <div className="absolute -left-[23px] top-1 w-3 h-3 rounded-full bg-cyan-500 border-2 border-[var(--background)]"></div>
          <div className="text-xs font-semibold text-[var(--foreground)]">Response Generation</div>
          <div className="text-[10px] text-[var(--muted-fg)]">Streaming to client</div>
        </div>
      </div>
    </div>
  );
}

function LogsPane({ d }: { d: any }) {
  return (
    <div className="flex flex-col gap-4">
      <JsonBlock data={d?.execution_plan} label="Full Execution Plan" />
      <JsonBlock data={d?.executor_metrics} label="Executor Metrics" />
      <JsonBlock data={d?.retrieval} label="Retrieval Data" />
      <JsonBlock data={d} label="Raw Debug Metadata" />
    </div>
  );
}

function ErrorsPane({ d }: { d: any }) {
  const errors = d?.errors || [];
  const toolGraph = d?.tool_graph || [];
  const failedSteps = toolGraph.filter((s: any) => !s.success);
  return (
    <div className="flex flex-col gap-4">
      {errors.length === 0 && failedSteps.length === 0 ? (
        <div className="text-xs text-[var(--success)] font-medium flex items-center gap-2 p-3 bg-[var(--success)]/5 border border-[var(--success)]/20 rounded-lg">
          <Activity size={14} /> No errors in this pipeline execution
        </div>
      ) : (
        <>
          {failedSteps.length > 0 && (
            <div>
              <div className="text-[10px] uppercase font-bold tracking-wider text-[var(--danger)] mb-1.5">Failed Steps</div>
              {failedSteps.map((step: any, i: number) => (
                <div key={i} className="p-3 bg-[var(--danger)]/5 border border-[var(--danger)]/20 rounded-lg mb-2">
                  <div className="text-xs font-mono font-semibold text-[var(--danger)]">{step.tool}</div>
                  {step.error && <div className="text-[11px] font-mono text-[var(--foreground)] mt-1 break-all">{step.error}</div>}
                </div>
              ))}
            </div>
          )}
          {errors.length > 0 && (
            <div>
              <div className="text-[10px] uppercase font-bold tracking-wider text-[var(--danger)] mb-1.5">Pipeline Errors</div>
              {errors.map((err: string, i: number) => (
                <pre key={i} className="text-[11px] font-mono text-[var(--danger)] bg-[var(--danger)]/5 border border-[var(--danger)]/20 rounded-md p-3 whitespace-pre-wrap break-all mb-2">
                  {err}
                </pre>
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main Component
// ---------------------------------------------------------------------------

const MIN_HEIGHT = 200;
const DEFAULT_HEIGHT = 340;
const MAX_HEIGHT_RATIO = 0.75;

export function DevPanel({ debugMetadata, isOpen, onClose }: DevPanelProps) {
  const [activeTab, setActiveTab] = useState<TabId>('overview');
  const [height, setHeight] = useState(DEFAULT_HEIGHT);
  const [isMaximized, setIsMaximized] = useState(false);
  const isDragging = useRef(false);
  const startY = useRef(0);
  const startHeight = useRef(0);
  const panelRef = useRef<HTMLDivElement>(null);

  // Drag resize
  const onMouseDown = useCallback((e: React.MouseEvent) => {
    isDragging.current = true;
    startY.current = e.clientY;
    startHeight.current = height;
    document.body.style.cursor = 'row-resize';
    document.body.style.userSelect = 'none';
    e.preventDefault();
  }, [height]);

  useEffect(() => {
    const onMouseMove = (e: MouseEvent) => {
      if (!isDragging.current) return;
      const delta = startY.current - e.clientY;
      const maxHeight = window.innerHeight * MAX_HEIGHT_RATIO;
      const newHeight = Math.min(maxHeight, Math.max(MIN_HEIGHT, startHeight.current + delta));
      setHeight(newHeight);
      setIsMaximized(false);
    };

    const onMouseUp = () => {
      isDragging.current = false;
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
    };

    document.addEventListener('mousemove', onMouseMove);
    document.addEventListener('mouseup', onMouseUp);
    return () => {
      document.removeEventListener('mousemove', onMouseMove);
      document.removeEventListener('mouseup', onMouseUp);
    };
  }, []);

  const toggleMaximize = () => {
    if (isMaximized) {
      setHeight(DEFAULT_HEIGHT);
      setIsMaximized(false);
    } else {
      setHeight(window.innerHeight * MAX_HEIGHT_RATIO);
      setIsMaximized(true);
    }
  };

  if (!isOpen || !debugMetadata) return null;

  const d = debugMetadata;

  const renderTabContent = () => {
    switch (activeTab) {
      case 'overview': return <OverviewPane d={d} />;
      case 'planner': return <PlannerPane d={d} />;
      case 'execution': return <ExecutionPane d={d} />;
      case 'tools': return <ToolsPane d={d} />;
      case 'retrieval': return <RetrievalPane d={d} />;
      case 'chunks': return <ChunksPane d={d} />;
      case 'prompt': return <PromptPane d={d} />;
      case 'tokens': return <TokensPane d={d} />;
      case 'latency': return <LatencyPane d={d} />;
      case 'timeline': return <TimelinePane d={d} />;
      case 'logs': return <LogsPane d={d} />;
      case 'errors': return <ErrorsPane d={d} />;
    }
  };

  // Count errors for badge
  const errorCount = (d?.errors?.length || 0) + (d?.tool_graph || []).filter((s: any) => !s.success).length;

  return (
    <div
      ref={panelRef}
      className="absolute bottom-0 left-0 right-0 z-50 flex flex-col border-t border-[var(--border-strong)] bg-[var(--surface)] shadow-[0_-4px_20px_rgba(0,0,0,0.4)]"
      style={{ height: `${height}px` }}
    >
      {/* Drag Handle */}
      <div
        className="flex items-center justify-center h-2 cursor-row-resize hover:bg-[var(--surface-hover)] transition-colors group"
        onMouseDown={onMouseDown}
      >
        <GripHorizontal size={14} className="text-[var(--muted-fg)] opacity-40 group-hover:opacity-100 transition-opacity" />
      </div>

      {/* Header with Tabs */}
      <div className="flex items-center border-b border-[var(--border)] px-2 gap-1 shrink-0">
        <div className="flex items-center gap-1 overflow-x-auto flex-1 py-1">
          {TABS.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-md text-[11px] font-medium whitespace-nowrap transition-all cursor-pointer ${activeTab === tab.id
                  ? 'bg-[var(--surface-active)] text-[var(--foreground)] border border-[var(--border-strong)]'
                  : 'text-[var(--muted-fg)] hover:text-[var(--foreground)] hover:bg-[var(--surface-hover)]'
                }`}
            >
              {tab.icon}
              {tab.label}
              {tab.id === 'errors' && errorCount > 0 && (
                <span className="ml-0.5 px-1 py-0 rounded bg-[var(--danger)] text-white text-[9px] font-bold">
                  {errorCount}
                </span>
              )}
            </button>
          ))}
        </div>
        <div className="flex items-center gap-1 pl-2 border-l border-[var(--border)] ml-1">
          <button onClick={toggleMaximize} className="p-1 text-[var(--muted-fg)] hover:text-[var(--foreground)] hover:bg-[var(--surface-hover)] rounded transition-colors cursor-pointer" title={isMaximized ? 'Restore' : 'Maximize'}>
            {isMaximized ? <Minimize2 size={13} /> : <Maximize2 size={13} />}
          </button>
          <button onClick={onClose} className="p-1 text-[var(--muted-fg)] hover:text-[var(--danger)] hover:bg-[var(--surface-hover)] rounded transition-colors cursor-pointer" title="Close">
            <X size={13} />
          </button>
        </div>
      </div>

      {/* Tab Content */}
      <div className="flex-1 overflow-y-auto p-4 text-[var(--foreground)]">
        {renderTabContent()}
      </div>
    </div>
  );
}
