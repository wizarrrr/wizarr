import React from 'react';
import { Handle, Node, Position } from 'reactflow';

interface CustomNodeProps {
    data: {
        label?: string;
    };
    id: string;
    type: string;
}

const CustomNode = ({ data, id, type }: CustomNodeProps) => {
  return (
    <div className="bg-white px-4 dark:bg-gray-800 dark:text-white p-2 rounded shadow-lg">
      <Handle type="source" position={Position.Top} id={`${id}-out`} style={{ background: '#555' }} />
      <div>
        {data.label ?? `Node ${id}`}
      </div>
      <Handle type="target" position={Position.Bottom} id={`${id}-in`} style={{ background: '#555' }} />
    </div>
  );
};

export default CustomNode;