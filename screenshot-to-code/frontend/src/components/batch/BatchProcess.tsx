import React, { useState } from "react";
import { Button } from "../ui/button";
import { Input } from "../ui/input";
import toast from "react-hot-toast";

interface TaskInfo {
  task_id: string;
  path: string;
  has_checkpoints: boolean;
  has_output: boolean;
  checkpoint_count: number;
}

interface BatchProcessProps {
  backendUrl: string;
}

const BatchProcess: React.FC<BatchProcessProps> = ({ backendUrl }) => {
  const [tasks, setTasks] = useState<TaskInfo[]>([]);
  const [loading, setLoading] = useState(false);
  const [processing, setProcessing] = useState<string | null>(null);
  const [apiKey, setApiKey] = useState("");
  const [baseDir, setBaseDir] = useState("");

  // 加载task列表
  const loadTasks = async () => {
    try {
      setLoading(true);
      const url = baseDir
        ? `${backendUrl}/api/tasks?base_dir=${encodeURIComponent(baseDir)}`
        : `${backendUrl}/api/tasks`;
      
      const response = await fetch(url);
      if (!response.ok) {
        throw new Error("Failed to load tasks");
      }
      
      const data = await response.json();
      setTasks(data.tasks || []);
      toast.success(`Found ${data.tasks.length} tasks`);
    } catch (error) {
      console.error("Error loading tasks:", error);
      toast.error("Failed to load tasks");
    } finally {
      setLoading(false);
    }
  };

  // 处理单个task
  const processTask = async (task: TaskInfo) => {
    if (!apiKey.trim()) {
      toast.error("Please enter your OpenAI API key");
      return;
    }

    try {
      setProcessing(task.task_id);
      toast.loading(`Processing ${task.task_id}...`);

      const response = await fetch(`${backendUrl}/api/batch-process`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          task_dir: task.path,
          api_key: apiKey,
          model: "gpt-4-vision-preview",
        }),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || "Processing failed");
      }

      const result = await response.json();
      toast.dismiss();
      toast.success(`Successfully processed ${task.task_id}`);
      
      // 刷新task列表
      await loadTasks();
    } catch (error: any) {
      toast.dismiss();
      console.error("Error processing task:", error);
      toast.error(`Failed to process ${task.task_id}: ${error.message}`);
    } finally {
      setProcessing(null);
    }
  };

  // 批量处理所有tasks
  const processAllTasks = async () => {
    if (!apiKey.trim()) {
      toast.error("Please enter your OpenAI API key");
      return;
    }

    const tasksToProcess = tasks.filter(t => t.has_checkpoints && !t.has_output);
    if (tasksToProcess.length === 0) {
      toast.error("No tasks to process");
      return;
    }

    try {
      toast.loading(`Processing ${tasksToProcess.length} tasks...`);
      
      for (const task of tasksToProcess) {
        setProcessing(task.task_id);
        await processTask(task);
      }
      
      toast.dismiss();
      toast.success("All tasks processed successfully");
    } catch (error) {
      toast.dismiss();
      toast.error("Failed to process all tasks");
    } finally {
      setProcessing(null);
    }
  };

  return (
    <div className="p-6 max-w-6xl mx-auto">
      <h1 className="text-3xl font-bold mb-6">Batch Process Tasks</h1>
      
      {/* 配置区域 */}
      <div className="mb-6 p-4 bg-gray-50 dark:bg-gray-800 rounded-lg">
        <h2 className="text-xl font-semibold mb-4">Configuration</h2>
        
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-2">
              OpenAI API Key
            </label>
            <Input
              type="password"
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              placeholder="sk-..."
              className="w-full"
            />
          </div>
          
          <div>
            <label className="block text-sm font-medium mb-2">
              Base Directory (optional)
            </label>
            <Input
              type="text"
              value={baseDir}
              onChange={(e) => setBaseDir(e.target.value)}
              placeholder="/path/to/tasks"
              className="w-full"
            />
            <p className="text-xs text-gray-500 mt-1">
              Leave empty to use default directory
            </p>
          </div>
          
          <div className="flex gap-2">
            <Button onClick={loadTasks} disabled={loading}>
              {loading ? "Loading..." : "Load Tasks"}
            </Button>
            <Button
              onClick={processAllTasks}
              disabled={processing || tasks.length === 0}
              variant="secondary"
            >
              Process All
            </Button>
          </div>
        </div>
      </div>

      {/* Task列表 */}
      <div className="bg-white dark:bg-gray-900 rounded-lg shadow">
        <div className="p-4 border-b dark:border-gray-700">
          <h2 className="text-xl font-semibold">
            Tasks ({tasks.length})
          </h2>
        </div>
        
        {tasks.length === 0 ? (
          <div className="p-8 text-center text-gray-500">
            No tasks found. Click "Load Tasks" to scan for tasks.
          </div>
        ) : (
          <div className="divide-y dark:divide-gray-700">
            {tasks.map((task) => (
              <div
                key={task.task_id}
                className="p-4 flex items-center justify-between hover:bg-gray-50 dark:hover:bg-gray-800"
              >
                <div className="flex-1">
                  <h3 className="font-medium">{task.task_id}</h3>
                  <p className="text-sm text-gray-500 mt-1">
                    {task.path}
                  </p>
                  <div className="flex gap-4 mt-2 text-sm">
                    <span className={task.has_checkpoints ? "text-green-600" : "text-red-600"}>
                      {task.checkpoint_count} checkpoints
                    </span>
                    <span className={task.has_output ? "text-blue-600" : "text-gray-400"}>
                      {task.has_output ? "Output generated" : "No output"}
                    </span>
                  </div>
                </div>
                
                <div className="flex gap-2">
                  {task.has_output && (
                    <Button
                      variant="outline"
                      onClick={() => window.open(`file://${task.path}/output`)}
                    >
                      View Output
                    </Button>
                  )}
                  <Button
                    onClick={() => processTask(task)}
                    disabled={processing !== null || !task.has_checkpoints}
                  >
                    {processing === task.task_id ? "Processing..." : "Process"}
                  </Button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* 使用说明 */}
      <div className="mt-6 p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
        <h3 className="font-semibold mb-2">How to use:</h3>
        <ol className="list-decimal list-inside space-y-2 text-sm">
          <li>Enter your OpenAI API key</li>
          <li>Click "Load Tasks" to scan for task directories</li>
          <li>Click "Process" on individual tasks or "Process All" to process all tasks</li>
          <li>Generated Vue3+Vite projects will be saved to each task's output/ directory</li>
        </ol>
      </div>
    </div>
  );
};

export default BatchProcess;
