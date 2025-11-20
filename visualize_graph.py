import json
from neo4j import GraphDatabase
import config
from typing import Optional, Dict, List

driver = GraphDatabase.driver(
    config.NEO4J_URI,
    auth=(config.NEO4J_USER, config.NEO4J_PASSWORD)
)

def get_graph_data(limit: int = 100, node_type: Optional[str] = None) -> Dict:
    """
    Fetch graph data from Neo4j
    
    Args:
        limit: Maximum number of nodes to fetch
        node_type: Optional filter by node type
    
    Returns:
        Dictionary with nodes and relationships
    """
    with driver.session() as session:
        # Build query based on filters
        if node_type:
            node_query = f"""
                MATCH (n:Entity)
                WHERE n.type = $node_type
                RETURN n.id AS id, n.name AS name, n.type AS type, 
                       n.description AS description, labels(n) AS labels
                LIMIT $limit
            """
            params = {"node_type": node_type, "limit": limit}
        else:
            node_query = """
                MATCH (n:Entity)
                RETURN n.id AS id, n.name AS name, n.type AS type, 
                       n.description AS description, labels(n) AS labels
                LIMIT $limit
            """
            params = {"limit": limit}
        
        # Get nodes
        result = session.run(node_query, params)
        nodes = []
        node_ids = set()
        
        for record in result:
            node_id = record["id"]
            node_ids.add(node_id)
            nodes.append({
                "id": node_id,
                "name": record["name"] or node_id,
                "type": record["type"] or "Unknown",
                "description": record["description"] or "",
                "labels": record["labels"]
            })
        
        # Get relationships between these nodes
        if node_ids:
            rel_query = """
                MATCH (a:Entity)-[r]->(b:Entity)
                WHERE a.id IN $node_ids AND b.id IN $node_ids
                RETURN a.id AS source, b.id AS target, type(r) AS type
            """
            result = session.run(rel_query, {"node_ids": list(node_ids)})
            
            relationships = []
            for record in result:
                relationships.append({
                    "source": record["source"],
                    "target": record["target"],
                    "type": record["type"]
                })
        else:
            relationships = []
    
    return {
        "nodes": nodes,
        "relationships": relationships
    }

def generate_graph_visualization(limit: int = 100, node_type: Optional[str] = None) -> str:
    """
    Generate interactive HTML visualization using D3.js
    
    Args:
        limit: Maximum number of nodes
        node_type: Optional filter by type
    
    Returns:
        HTML string with embedded D3.js visualization
    """
    # Get graph data
    graph_data = get_graph_data(limit=limit, node_type=node_type)
    
    # Generate color mapping for node types
    types = list(set(node["type"] for node in graph_data["nodes"]))
    colors = [
        "#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd",
        "#8c564b", "#e377c2", "#7f7f7f", "#bcbd22", "#17becf"
    ]
    type_colors = {t: colors[i % len(colors)] for i, t in enumerate(types)}
    
    # HTML template with D3.js visualization
    html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Vietnam Travel Knowledge Graph</title>
    <script src="https://d3js.org/d3.v7.min.js"></script>
    <style>
        body {{
            margin: 0;
            padding: 0;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            overflow: hidden;
        }}
        
        #container {{
            width: 100vw;
            height: 100vh;
            display: flex;
            flex-direction: column;
        }}
        
        #header {{
            background: rgba(255, 255, 255, 0.95);
            padding: 20px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            z-index: 1000;
        }}
        
        h1 {{
            margin: 0 0 10px 0;
            color: #333;
            font-size: 28px;
        }}
        
        #stats {{
            color: #666;
            font-size: 14px;
        }}
        
        #legend {{
            position: absolute;
            top: 120px;
            right: 20px;
            background: rgba(255, 255, 255, 0.95);
            padding: 15px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            max-width: 250px;
            z-index: 1000;
        }}
        
        .legend-title {{
            font-weight: bold;
            margin-bottom: 10px;
            color: #333;
        }}
        
        .legend-item {{
            display: flex;
            align-items: center;
            margin: 5px 0;
            font-size: 12px;
        }}
        
        .legend-color {{
            width: 20px;
            height: 20px;
            border-radius: 50%;
            margin-right: 8px;
            border: 2px solid #fff;
            box-shadow: 0 1px 3px rgba(0,0,0,0.2);
        }}
        
        #graph {{
            flex: 1;
            background: white;
            position: relative;
        }}
        
        .node {{
            cursor: pointer;
            stroke: #fff;
            stroke-width: 2px;
        }}
        
        .node:hover {{
            stroke: #333;
            stroke-width: 3px;
        }}
        
        .link {{
            stroke: #999;
            stroke-opacity: 0.6;
            stroke-width: 1.5px;
        }}
        
        .node-label {{
            font-size: 10px;
            pointer-events: none;
            fill: #333;
            text-shadow: 0 1px 0 #fff, 1px 0 0 #fff, 0 -1px 0 #fff, -1px 0 0 #fff;
        }}
        
        .tooltip {{
            position: absolute;
            padding: 12px;
            background: rgba(0, 0, 0, 0.9);
            color: white;
            border-radius: 6px;
            pointer-events: none;
            font-size: 12px;
            max-width: 300px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.3);
            z-index: 2000;
        }}
        
        .tooltip-title {{
            font-weight: bold;
            margin-bottom: 5px;
            font-size: 14px;
        }}
        
        .tooltip-type {{
            color: #ffd700;
            font-size: 11px;
            margin-bottom: 5px;
        }}
        
        .tooltip-desc {{
            font-size: 11px;
            line-height: 1.4;
        }}
        
        #controls {{
            position: absolute;
            bottom: 20px;
            left: 20px;
            background: rgba(255, 255, 255, 0.95);
            padding: 15px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            z-index: 1000;
        }}
        
        button {{
            background: #667eea;
            color: white;
            border: none;
            padding: 8px 16px;
            margin: 5px;
            border-radius: 4px;
            cursor: pointer;
            font-size: 12px;
        }}
        
        button:hover {{
            background: #764ba2;
        }}
    </style>
</head>
<body>
    <div id="container">
        <div id="header">
            <h1>🌏 Vietnam Travel Knowledge Graph</h1>
            <div id="stats">
                <span><strong>{len(graph_data["nodes"])}</strong> Entities</span> • 
                <span><strong>{len(graph_data["relationships"])}</strong> Relationships</span> • 
                <span><strong>{len(types)}</strong> Types</span>
            </div>
        </div>
        
        <div id="legend">
            <div class="legend-title">Entity Types</div>
            {''.join([f'<div class="legend-item"><div class="legend-color" style="background:{type_colors[t]}"></div><span>{t}</span></div>' for t in sorted(types)])}
        </div>
        
        <div id="controls">
            <button onclick="resetZoom()">Reset View</button>
            <button onclick="centerGraph()">Center</button>
        </div>
        
        <div id="graph"></div>
    </div>
    
    <script>
        const graphData = {json.dumps(graph_data)};
        const typeColors = {json.dumps(type_colors)};
        
        const width = window.innerWidth;
        const height = window.innerHeight - 100;
        
        const svg = d3.select("#graph")
            .append("svg")
            .attr("width", width)
            .attr("height", height);
        
        const g = svg.append("g");
        
        // Zoom behavior
        const zoom = d3.zoom()
            .scaleExtent([0.1, 10])
            .on("zoom", (event) => {{
                g.attr("transform", event.transform);
            }});
        
        svg.call(zoom);
        
        // Create arrow markers
        svg.append("defs").selectAll("marker")
            .data(["arrow"])
            .enter().append("marker")
            .attr("id", d => d)
            .attr("viewBox", "0 -5 10 10")
            .attr("refX", 20)
            .attr("refY", 0)
            .attr("markerWidth", 6)
            .attr("markerHeight", 6)
            .attr("orient", "auto")
            .append("path")
            .attr("d", "M0,-5L10,0L0,5")
            .attr("fill", "#999");
        
        // Force simulation
        const simulation = d3.forceSimulation(graphData.nodes)
            .force("link", d3.forceLink(graphData.relationships)
                .id(d => d.id)
                .distance(100))
            .force("charge", d3.forceManyBody().strength(-300))
            .force("center", d3.forceCenter(width / 2, height / 2))
            .force("collision", d3.forceCollide().radius(30));
        
        // Links
        const link = g.append("g")
            .selectAll("line")
            .data(graphData.relationships)
            .enter().append("line")
            .attr("class", "link")
            .attr("marker-end", "url(#arrow)");
        
        // Nodes
        const node = g.append("g")
            .selectAll("circle")
            .data(graphData.nodes)
            .enter().append("circle")
            .attr("class", "node")
            .attr("r", 8)
            .attr("fill", d => typeColors[d.type] || "#999")
            .call(d3.drag()
                .on("start", dragstarted)
                .on("drag", dragged)
                .on("end", dragended));
        
        // Labels
        const label = g.append("g")
            .selectAll("text")
            .data(graphData.nodes)
            .enter().append("text")
            .attr("class", "node-label")
            .text(d => d.name.substring(0, 20) + (d.name.length > 20 ? "..." : ""));
        
        // Tooltip
        const tooltip = d3.select("body").append("div")
            .attr("class", "tooltip")
            .style("opacity", 0);
        
        node.on("mouseover", function(event, d) {{
            tooltip.transition().duration(200).style("opacity", 1);
            tooltip.html(`
                <div class="tooltip-title">${{d.name}}</div>
                <div class="tooltip-type">Type: ${{d.type}}</div>
                <div class="tooltip-desc">${{d.description || "No description"}}</div>
            `)
            .style("left", (event.pageX + 10) + "px")
            .style("top", (event.pageY - 28) + "px");
            
            d3.select(this).attr("r", 12);
        }})
        .on("mouseout", function(d) {{
            tooltip.transition().duration(200).style("opacity", 0);
            d3.select(this).attr("r", 8);
        }});
        
        // Update positions
        simulation.on("tick", () => {{
            link
                .attr("x1", d => d.source.x)
                .attr("y1", d => d.source.y)
                .attr("x2", d => d.target.x)
                .attr("y2", d => d.target.y);
            
            node
                .attr("cx", d => d.x)
                .attr("cy", d => d.y);
            
            label
                .attr("x", d => d.x)
                .attr("y", d => d.y - 12);
        }});
        
        // Drag functions
        function dragstarted(event, d) {{
            if (!event.active) simulation.alphaTarget(0.3).restart();
            d.fx = d.x;
            d.fy = d.y;
        }}
        
        function dragged(event, d) {{
            d.fx = event.x;
            d.fy = event.y;
        }}
        
        function dragended(event, d) {{
            if (!event.active) simulation.alphaTarget(0);
            d.fx = null;
            d.fy = null;
        }}
        
        // Control functions
        function resetZoom() {{
            svg.transition().duration(750).call(
                zoom.transform,
                d3.zoomIdentity
            );
        }}
        
        function centerGraph() {{
            const bounds = g.node().getBBox();
            const fullWidth = width;
            const fullHeight = height;
            const midX = bounds.x + bounds.width / 2;
            const midY = bounds.y + bounds.height / 2;
            
            const scale = 0.8 / Math.max(bounds.width / fullWidth, bounds.height / fullHeight);
            const translate = [fullWidth / 2 - scale * midX, fullHeight / 2 - scale * midY];
            
            svg.transition().duration(750).call(
                zoom.transform,
                d3.zoomIdentity.translate(translate[0], translate[1]).scale(scale)
            );
        }}
        
        // Initial center
        setTimeout(centerGraph, 1000);
    </script>
</body>
</html>
    """
    
    return html

def save_visualization_html(filename: str = "graph_visualization.html", limit: int = 100):
    """Save visualization to HTML file"""
    html = generate_graph_visualization(limit=limit)
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"✅ Visualization saved to {filename}")

if __name__ == "__main__":
    # Generate and save visualization
    save_visualization_html("graph_visualization.html", limit=150)
    print("Open graph_visualization.html in your browser to view the graph!")