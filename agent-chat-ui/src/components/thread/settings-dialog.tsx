"use client";

import * as React from "react";
import { useState, useEffect, useCallback } from "react";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { PasswordInput } from "@/components/ui/password-input";
import { Settings2 } from "lucide-react";
import { toast } from "sonner";
import { CustomAPIClient } from "@/providers/client";

// Create API client instance
function createApiClient(): CustomAPIClient {
  const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
  return new CustomAPIClient(apiUrl, undefined);
}

export interface AgentConfig {
  session?: {
    checkpoint_path?: string;
    single_user?: boolean;
  };
  planner?: {
    hitl_enabled?: boolean;
  };
  executor?: {
    max_retries?: number;
    verbose?: boolean;
  };
  tools?: {
    default_category?: string;
    auto_register?: boolean;
  };
}

export interface LlmConfig {
  default?: {
    provider?: string;
    model?: string;
    base_url?: string;
    api_key?: string;
  };
  planner?: {
    temperature?: number;
    max_tokens?: number;
  };
  executor?: {
    temperature?: number;
    max_tokens?: number;
  };
}

interface SettingsDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function SettingsDialog({ open, onOpenChange }: SettingsDialogProps) {
  const [api] = useState(() => createApiClient());
  const [isLoading, setIsLoading] = useState(false);
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false);

  // LLM config state
  const [llmConfig, setLlmConfig] = useState<LlmConfig>({});

  // Agent config state
  const [agentConfig, setAgentConfig] = useState<AgentConfig>({});

  // Load config
  const loadConfig = useCallback(async () => {
    try {
      const config = await api.getConfig();
      setLlmConfig(config.llm);
      setAgentConfig(config.agent);
    } catch (error) {
      toast.error("Failed to load config", {
        description: error instanceof Error ? error.message : "Unknown error",
      });
    }
  }, [api]);

  useEffect(() => {
    if (open) {
      loadConfig();
    }
  }, [open, loadConfig]);

  const handleSave = async () => {
    setIsLoading(true);
    try {
      await api.updateConfig({
        llm: llmConfig,
        agent: agentConfig,
      });
      toast.success("Config saved");
      setHasUnsavedChanges(false);
      onOpenChange(false);
    } catch (error) {
      toast.error("Failed to save config", {
        description: error instanceof Error ? error.message : "Unknown error",
      });
    } finally {
      setIsLoading(false);
    }
  };

  const handleLlmChange = (section: keyof LlmConfig, field: string, value: any) => {
    setLlmConfig((prev) => {
      const newConfig = { ...prev };
      if (!newConfig[section]) {
        newConfig[section] = {};
      }
      (newConfig[section] as any)[field] = value;
      setHasUnsavedChanges(true);
      return newConfig;
    });
  };

  const handleAgentChange = (section: keyof AgentConfig, field: string, value: any) => {
    setAgentConfig((prev) => {
      const newConfig = { ...prev };
      if (!newConfig[section]) {
        newConfig[section] = {};
      }
      (newConfig[section] as any)[field] = value;
      setHasUnsavedChanges(true);
      return newConfig;
    });
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Settings2 className="h-5 w-5" />
            Settings
          </DialogTitle>
        </DialogHeader>

        <div className="grid gap-6 py-4">
          {/* LLM Config */}
          <section className="space-y-4">
            <h3 className="text-sm font-medium text-gray-500 uppercase tracking-wider">
              LLM Config
            </h3>

            {/* Default Config */}
            <div className="grid gap-4">
              <h4 className="text-sm font-semibold">Default</h4>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="llm-provider">Provider</Label>
                  <Input
                    id="llm-provider"
                    value={llmConfig.default?.provider || ""}
                    onChange={(e) => handleLlmChange("default", "provider", e.target.value)}
                    placeholder="deepseek"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="llm-model">Model</Label>
                  <Input
                    id="llm-model"
                    value={llmConfig.default?.model || ""}
                    onChange={(e) => handleLlmChange("default", "model", e.target.value)}
                    placeholder="deepseek-chat"
                  />
                </div>
              </div>
              <div className="space-y-2">
                <Label htmlFor="llm-base-url">Base URL</Label>
                <Input
                  id="llm-base-url"
                  value={llmConfig.default?.base_url || ""}
                  onChange={(e) => handleLlmChange("default", "base_url", e.target.value)}
                  placeholder="https://api.deepseek.com"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="llm-api-key">API Key</Label>
                <PasswordInput
                  id="llm-api-key"
                  value={llmConfig.default?.api_key || ""}
                  onChange={(e) => handleLlmChange("default", "api_key", e.target.value)}
                  placeholder="sk-xxx"
                />
              </div>
            </div>

            {/* Planner LLM Config */}
            <div className="grid gap-4 pt-2">
              <h4 className="text-sm font-semibold">Planner</h4>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="planner-temperature">Temperature</Label>
                  <Input
                    id="planner-temperature"
                    type="number"
                    step="0.1"
                    min="0"
                    max="2"
                    value={llmConfig.planner?.temperature ?? 0.1}
                    onChange={(e) => handleLlmChange("planner", "temperature", parseFloat(e.target.value))}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="planner-max-tokens">Max Tokens</Label>
                  <Input
                    id="planner-max-tokens"
                    type="number"
                    value={llmConfig.planner?.max_tokens ?? 65536}
                    onChange={(e) => handleLlmChange("planner", "max_tokens", parseInt(e.target.value))}
                  />
                </div>
              </div>
            </div>

            {/* Executor LLM Config */}
            <div className="grid gap-4 pt-2">
              <h4 className="text-sm font-semibold">Executor</h4>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="executor-temperature">Temperature</Label>
                  <Input
                    id="executor-temperature"
                    type="number"
                    step="0.1"
                    min="0"
                    max="2"
                    value={llmConfig.executor?.temperature ?? 0.3}
                    onChange={(e) => handleLlmChange("executor", "temperature", parseFloat(e.target.value))}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="executor-max-tokens">Max Tokens</Label>
                  <Input
                    id="executor-max-tokens"
                    type="number"
                    value={llmConfig.executor?.max_tokens ?? 65536}
                    onChange={(e) => handleLlmChange("executor", "max_tokens", parseInt(e.target.value))}
                  />
                </div>
              </div>
            </div>
          </section>

          {/* Agent Config */}
          <section className="space-y-4 pt-4 border-t">
            <h3 className="text-sm font-medium text-gray-500 uppercase tracking-wider">
              Agent Config
            </h3>

            {/* Planner Config */}
            <div className="grid gap-4">
              <h4 className="text-sm font-semibold">Planner</h4>
              <div className="flex items-center space-x-2">
                <Switch
                  id="planner-hitl"
                  checked={agentConfig.planner?.hitl_enabled ?? true}
                  onCheckedChange={(checked) => handleAgentChange("planner", "hitl_enabled", checked)}
                />
                <Label htmlFor="planner-hitl">Enable HITL (Human-in-the-loop)</Label>
              </div>
            </div>

            {/* Executor Config */}
            <div className="grid gap-4 pt-2">
              <h4 className="text-sm font-semibold">Executor</h4>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="executor-max-retries">Max Retries</Label>
                  <Input
                    id="executor-max-retries"
                    type="number"
                    min="0"
                    max="10"
                    value={agentConfig.executor?.max_retries ?? 3}
                    onChange={(e) => handleAgentChange("executor", "max_retries", parseInt(e.target.value))}
                  />
                </div>
                <div className="space-y-2">
                  <div className="flex items-center space-x-2 h-10">
                    <Switch
                      id="executor-verbose"
                      checked={agentConfig.executor?.verbose ?? false}
                      onCheckedChange={(checked) => handleAgentChange("executor", "verbose", checked)}
                    />
                    <Label htmlFor="executor-verbose">Verbose Log</Label>
                  </div>
                </div>
              </div>
            </div>
          </section>
        </div>

        <DialogFooter>
          <Button
            variant="outline"
            onClick={() => onOpenChange(false)}
          >
            Cancel
          </Button>
          <Button
            onClick={handleSave}
            disabled={isLoading || !hasUnsavedChanges}
          >
            {isLoading ? "Saving..." : "Save Config"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
