import 'reactflow/dist/style.css';

import { nanoid } from 'nanoid';
import React, { useCallback, useRef, useState } from 'react';
import ReactFlow, {
    addEdge, applyEdgeChanges, applyNodeChanges, Background, BackgroundVariant, Controls,
    DefaultEdgeOptions, Edge, EdgeChange, FitViewOptions, MiniMap, Node, NodeChange, NodeTypes,
    OnConnect, OnEdgesChange, OnNodesChange, ReactFlowInstance, ReactFlowProvider
} from 'reactflow';

import CustomNode from './nodes/custom';

const initialNodes: Node[] = JSON.parse(localStorage.getItem("nodes") ?? "[]");
const initialEdges: Edge[] = JSON.parse(localStorage.getItem("edges") ?? "[]");

const fitViewOptions: FitViewOptions = {
    padding: 0.2,
};

const defaultEdgeOptions: DefaultEdgeOptions = {
    animated: true,
    type: "step",
};

const nodeTypes: NodeTypes = {
    custom: CustomNode,
};

const edgeTypes = {};

function Flow() {
    const reactFlowWrapper = useRef(null);
    const [nodes, setNodes] = useState<Node[]>(initialNodes);
    const [edges, setEdges] = useState<Edge[]>(initialEdges);
    const [reactFlowInstance, setReactFlowInstance] =
        useState<ReactFlowInstance<any, any> | null>(null);

    const saveNodes = (nodes: Node[]) => {
        localStorage.setItem("nodes", JSON.stringify(nodes));
    };

    const saveEdges = (edges: Edge[]) => {
        localStorage.setItem("edges", JSON.stringify(edges));
    };

    const onNodesChange: OnNodesChange = useCallback(
        (changes) => {
            setNodes((nds) => {
                const newNodes = applyNodeChanges(changes, nds);
                saveNodes(newNodes);
                return newNodes;
            });
        },
        [setNodes]
    );

    const onEdgesChange: OnEdgesChange = useCallback(
        (changes) => {
            setEdges((eds) => {
                const newEdges = applyEdgeChanges(changes, eds);
                saveEdges(newEdges);
                return newEdges;
            });
        },
        [setEdges]
    );

    const onConnect: OnConnect = useCallback(
        (connection) => {
            setEdges((eds) => {
                const newEdges = addEdge(connection, eds);
                saveEdges(newEdges);
                return newEdges;
            });
        },
        [setEdges]
    );

    const onDragOver = useCallback((event: any) => {
        event.preventDefault();
        event.dataTransfer.dropEffect = "move";
    }, []);

    const onDrop = useCallback(
        (event: any) => {
            event.preventDefault();

            if (!reactFlowWrapper.current || !reactFlowInstance) {
                return;
            }

            const reactFlowBounds = (
                reactFlowWrapper.current as HTMLElement
            ).getBoundingClientRect();
            const type = event.dataTransfer.getData("application/reactflow");

            // check if the dropped element is valid
            if (typeof type === "undefined" || !type) {
                return;
            }

            const position = reactFlowInstance.project({
                x: event.clientX - reactFlowBounds.left,
                y: event.clientY - reactFlowBounds.top,
            });

            const newNode = {
                id: nanoid(10),
                type,
                position,
                data: { label: `${type} node` },
            };

            setNodes((nds) => nds.concat(newNode));
        },
        [reactFlowInstance]
    );

    const proOptions = { hideAttribution: true };

    return (
        <ReactFlowProvider>
            <div
                className="reactflow-wrapper w-full h-full"
                ref={reactFlowWrapper}
            >
                <ReactFlow
                    onInit={setReactFlowInstance}
                    onDrop={onDrop}
                    onDragOver={onDragOver}
                    nodes={nodes}
                    edges={edges}
                    onNodesChange={onNodesChange}
                    onEdgesChange={onEdgesChange}
                    onConnect={onConnect}
                    fitView
                    fitViewOptions={fitViewOptions}
                    defaultEdgeOptions={defaultEdgeOptions}
                    edgeTypes={edgeTypes}
                    nodeTypes={nodeTypes}
                    proOptions={proOptions}
                >
                    <Controls />
                    <Background
                        variant={BackgroundVariant.Dots}
                        gap={12}
                        size={1}
                    />
                </ReactFlow>
            </div>
        </ReactFlowProvider>
    );
}

export default Flow;
