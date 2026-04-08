import React from "react";
import type { TodoItem } from "@/types/api";

interface TodoListCardProps {
  todoList: TodoItem[];
}

export function TodoListCard({ todoList }: TodoListCardProps) {
  if (!todoList || todoList.length === 0) {
    return null;
  }

  return (
    <div className="max-w-full overflow-hidden rounded-lg border border-gray-200 bg-white">
      <table className="w-full border-collapse">
        <thead>
          <tr>
            <th
              className="bg-gray-100 px-3 py-2 text-left text-sm font-semibold text-gray-700"
              colSpan={2}
            >
              Task List
            </th>
          </tr>
        </thead>
        <tbody>
          {todoList.map((todo, index) => (
            // eslint-disable-next-line @typescript-eslint/no-unused-vars
            <React.Fragment key={todo.id}>
              <tr className="border-t border-gray-200">
                <td className="w-1/4 px-3 py-2 text-xs font-medium text-gray-500">
                  Task ID
                </td>
                <td className="px-3 py-2 font-mono text-xs text-gray-900">
                  {todo.id}
                </td>
              </tr>
              <tr className="border-t border-gray-200">
                <td className="px-3 py-2 text-xs font-medium text-gray-500">
                  Description
                </td>
                <td className="px-3 py-2 text-xs text-gray-900">
                  {todo.description}
                </td>
              </tr>
              <tr className="border-t border-gray-200">
                <td className="px-3 py-2 text-xs font-medium text-gray-500">
                  Tool
                </td>
                <td className="px-3 py-2 font-mono text-xs text-gray-900">
                  {todo.tool}
                </td>
              </tr>
              {index < todoList.length - 1 && (
                <tr className="border-t border-gray-100">
                  <td colSpan={2} className="bg-gray-50 px-3 py-1" />
                </tr>
              )}
            </React.Fragment>
          ))}
        </tbody>
      </table>
    </div>
  );
}
