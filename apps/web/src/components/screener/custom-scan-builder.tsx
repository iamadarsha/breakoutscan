"use client";

import { useState } from "react";
import { Plus, Play } from "lucide-react";
import { ConditionRow } from "./condition-row";
import { Button } from "@/components/ui/button";
import { PanelHeader } from "@/components/ui/panel-header";
import { cn } from "@/lib/cn";
import type { CustomScanCondition } from "@/lib/api-types";

interface Condition {
  id: number;
  indicator: string;
  operator: string;
  value: string;
}

interface CustomScanBuilderProps {
  onRun: (conditions: CustomScanCondition[], universe: string, timeframe: string) => void;
  isLoading?: boolean;
}

let nextId = 1;

export function CustomScanBuilder({ onRun, isLoading }: CustomScanBuilderProps) {
  const [conditions, setConditions] = useState<Condition[]>([
    { id: nextId++, indicator: "close", operator: "gt", value: "" },
  ]);
  const [universe, setUniverse] = useState("nifty500");
  const [timeframe, setTimeframe] = useState("daily");

  const addCondition = () => {
    setConditions((prev) => [
      ...prev,
      { id: nextId++, indicator: "close", operator: "gt", value: "" },
    ]);
  };

  const removeCondition = (id: number) => {
    setConditions((prev) => prev.filter((c) => c.id !== id));
  };

  const updateCondition = (
    id: number,
    field: "indicator" | "operator" | "value",
    val: string
  ) => {
    setConditions((prev) =>
      prev.map((c) => (c.id === id ? { ...c, [field]: val } : c))
    );
  };

  const handleRun = () => {
    const mapped: CustomScanCondition[] = conditions
      .filter((c) => c.value !== "")
      .map((c) => ({
        indicator: c.indicator,
        operator: c.operator,
        value: isNaN(Number(c.value)) ? c.value : Number(c.value),
      }));
    if (mapped.length > 0) {
      onRun(mapped, universe, timeframe);
    }
  };

  const selectClass = cn(
    "h-9 rounded-lg border border-border bg-card px-3 text-data text-text-primary outline-none transition-colors appearance-none cursor-pointer",
    "focus:border-accent hover:border-accent/40",
    "[&>option]:bg-card [&>option]:text-text-primary"
  );

  return (
    <div className="glass-card overflow-hidden">
      <PanelHeader title="Custom scan builder" meta="combine your own conditions" />
      <div className="p-4">
      <div className="mb-4 flex items-end gap-3">
        <div className="flex flex-col gap-1">
          <label htmlFor="scan-universe" className="text-micro font-semibold uppercase text-text-muted">
            Universe
          </label>
          <select
            id="scan-universe"
            value={universe}
            onChange={(e) => setUniverse(e.target.value)}
            className={selectClass}
          >
            <option value="nifty50">NIFTY 50</option>
            <option value="nifty500">NIFTY 500</option>
            <option value="all">All Stocks</option>
          </select>
        </div>
        <div className="flex flex-col gap-1">
          <label htmlFor="scan-timeframe" className="text-micro font-semibold uppercase text-text-muted">
            Timeframe
          </label>
          <select
            id="scan-timeframe"
            value={timeframe}
            onChange={(e) => setTimeframe(e.target.value)}
            className={selectClass}
          >
            <option value="1min">1 Minute</option>
            <option value="5min">5 Minutes</option>
            <option value="15min">15 Minutes</option>
            <option value="daily">Daily</option>
          </select>
        </div>
      </div>

      <div className="mb-4 space-y-2">
        {conditions.map((c) => (
          <ConditionRow
            key={c.id}
            indicator={c.indicator}
            operator={c.operator}
            value={c.value}
            onChange={(field, val) => updateCondition(c.id, field, val)}
            onRemove={() => removeCondition(c.id)}
            canRemove={conditions.length > 1}
          />
        ))}
      </div>

      <div className="flex items-center gap-3">
        <button
          onClick={addCondition}
          className="flex h-8 items-center gap-1.5 rounded-lg border border-dashed border-border px-3 text-label font-medium text-text-secondary transition-colors hover:border-accent hover:text-accent"
        >
          <Plus className="h-3.5 w-3.5" />
          Add Condition
        </button>

        <Button
          onClick={handleRun}
          disabled={isLoading}
          className="ml-auto flex items-center gap-2"
        >
          <Play className="h-3.5 w-3.5" />
          {isLoading ? "Running..." : "Run Scan"}
        </Button>
      </div>
      </div>
    </div>
  );
}
