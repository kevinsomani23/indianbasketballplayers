import json

def render_social_html(card_data, graphic_type="player", theme="dark"):
    """
    Generates the HTML for the Social Studio card.
    
    Args:
        card_data (dict): Dictionary containing the stats/info to display.
        graphic_type (str): 'player' or 'match'.
        theme (str): 'dark', 'light', or 'brand'.
    """
    
    # Serialize data for JS injection
    json_data = json.dumps(card_data)
    
    html_content = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/html-to-image/1.11.11/html-to-image.min.js"></script>
    <script>
        tailwind.config = {{
            theme: {{ 
                extend: {{ 
                    colors: {{ 
                        brand: '#ff8533', 
                        dark: '#000000', 
                        panel: 'rgba(18, 18, 18, 0.85)', 
                        accent: '#3b82f6',
                        glassBorder: 'rgba(255, 255, 255, 0.1)'
                    }} 
                }} 
            }}
        }}
    </script>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;500;600;700&family=Outfit:wght@400;500;600;700;800;900&display=swap" rel="stylesheet">
    <style>
        body {{ 
            background-color: transparent; 
            font-family: 'Space Grotesk', sans-serif; 
            margin: 0;
            padding: 0;
            overflow: hidden;
        }}
        .glass-background {{
            background: rgba(18, 18, 18, 0.85);
            backdrop-filter: blur(16px);
            border: 1px solid rgba(255, 255, 255, 0.1);
        }}
        ::-webkit-scrollbar {{ display: none; }}
        
        #card {{
            width: 1080px;
            height: 1080px;
            background-color: #000000;
            position: relative;
            overflow: hidden;
            display: flex;
            flex-direction: column;
            padding: 60px;
        }}

        .noise-overlay {{
            position: absolute;
            inset: 0;
            background: url('https://grainy-gradients.vercel.app/noise.svg');
            opacity: 0.05;
            pointer-events: none;
            mix-blend-overlay: overlay;
            z-index: 5;
        }}

        .logo-container img {{
            height: 48px;
            width: auto;
            object-fit: contain;
        }}
        
        .table-container {{
            background: rgba(18, 18, 18, 0.4);
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 16px;
            overflow: hidden;
        }}
        
        table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 14px;
        }}
        
        th {{
            background: rgba(0, 0, 0, 0.3);
            color: #707070;
            text-transform: uppercase;
            font-size: 12px;
            letter-spacing: 0.1em;
            padding: 20px 15px;
            text-align: center;
            border-bottom: 2px solid rgba(255, 255, 255, 0.05);
        }}
        
        td {{
            padding: 16px 15px;
            color: white;
            border-bottom: 1px solid rgba(255, 255, 255, 0.05);
            text-align: center;
            font-family: 'Outfit', sans-serif;
        }}
        
        .player-cell {{
            text-align: left;
            padding-left: 25px;
            font-family: 'Space Grotesk', sans-serif;
            font-weight: 700;
        }}

        .highlight-cell {{
            background: rgba(255, 133, 51, 0.45);
            border-bottom: 2px solid #ff8533;
            font-weight: 800;
            text-shadow: 0 0 10px rgba(255, 133, 51, 0.5);
        }}
    </style>
</head>
<body class="flex items-center justify-center min-h-screen bg-transparent">

    <div id="card-container" class="relative group">
        <!-- CARD -->
        <div id="card">
            <!-- Content Injected via JS -->
        </div>
        
        <!-- Download Button Overlay -->
        <div class="fixed bottom-10 left-0 right-0 flex justify-center z-50">
            <button onclick="downloadCard()" class="bg-[#ff8533] text-white font-bold py-3 px-8 rounded-full shadow-2xl hover:scale-105 transition-transform flex items-center gap-3">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
                EXPORT FOR INSTAGRAM
            </button>
        </div>
    </div>

    <script>
        const DATA = {json_data};
        const TYPE = "{graphic_type}";
        const THEME = "{theme}";
        
        window.onload = function() {{
            renderCard();
        }};

        function renderCard() {{
            const card = document.getElementById('card');
            if (TYPE === 'table') renderTableCard(card);
            // player/match can be updated later if needed
        }}

        function renderTableCard(card) {{
            const d = DATA;
            const headers = d.headers || [];
            const rows = d.rows || [];
            const title = d.title || "LEADERBOARD";
            const subtitle = d.subtitle || "75TH SENIOR NATIONALS";

            card.innerHTML = `
                <div class="noise-overlay"></div>
                
                <!-- Header Component -->
                <div class="flex justify-between items-start mb-12 relative z-10 w-full">
                    <div>
                        <div class="flex items-center gap-2 mb-2">
                            <span class="text-brand font-black text-xs tracking-[0.3em] uppercase">Powered by Kev Media</span>
                        </div>
                        <h1 class="text-5xl font-black text-white tracking-tight uppercase leading-none">${{title}}</h1>
                        <p class="text-lg text-white/40 mt-3 font-medium uppercase tracking-[0.2em]">${{subtitle}}</p>
                    </div>
                    
                    <div class="flex items-center gap-6">
                        <!-- Tappa Logo Placeholder -->
                        <div class="flex flex-col items-end">
                            <div class="text-xs font-bold text-white/20 uppercase tracking-widest mb-2">Made by Tappa</div>
                            <div class="flex gap-4 items-center">
                                <div class="w-12 h-12 rounded-lg bg-brand flex items-center justify-center font-black text-white text-xl">T</div>
                                <div class="w-12 h-12 rounded-lg bg-white flex items-center justify-center font-black text-black text-xl">K</div>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Table Component -->
                <div class="flex-1 w-full relative z-10 overflow-hidden table-container">
                    <table>
                        <thead>
                            <tr>
                                ${{headers.map(h => `<th>${{h}}</th>`).join('')}}
                            </tr>
                        </thead>
                        <tbody>
                            ${{rows.map((row, i) => `
                                <tr style="background: ${{i % 2 === 0 ? 'rgba(255,255,255,0.01)' : 'transparent'}}">
                                    ${{headers.map((h, j) => {{
                                        let val = row[h];
                                        let classes = j === 0 ? 'player-cell' : '';
                                        
                                        // Simple logic to highlight high scores (could be improved)
                                        if (h === 'PTS' && parseFloat(val) >= 25) classes += ' highlight-cell';
                                        if (h === 'GmScr' && parseFloat(val) >= 20) classes += ' highlight-cell';
                                        
                                        return `<td class="${{classes}}">${{val}}</td>`;
                                    }}).join('')}}
                                </tr>
                            `).join('')}}
                        </tbody>
                    </table>
                </div>

                <!-- Footer Component -->
                <div class="mt-auto pt-10 flex justify-between items-end relative z-10 w-full">
                    <div class="flex flex-col gap-1">
                        <span class="text-white/20 font-bold tracking-[0.4em] text-xs">TAPPA PRO ANALYTICS</span>
                        <span class="text-white font-mono text-sm">INSTAGRAM / @THEKEVMEDIA</span>
                    </div>
                    <div class="text-right">
                        <span class="text-brand font-black text-2xl tracking-tighter">KEV MEDIA x TAPPA</span>
                    </div>
                </div>
            `;
        }}

        function downloadCard() {{
            const card = document.getElementById('card');
            const title = DATA.title || "tappa-stat-card";
            const filename = title.toLowerCase().replace(/\s+/g, '-') + '.png';
            
            // Explicitly set dimensions and use high pixel ratio for IG quality
            htmlToImage.toPng(card, {{ 
                quality: 1.0, 
                pixelRatio: 2,
                width: 1080,
                height: 1080,
                style: {{
                    transform: 'scale(1)',
                    transformOrigin: 'top left'
                }}
            }})
            .then(function (dataUrl) {{
                var link = document.createElement('a');
                link.download = filename;
                link.href = dataUrl;
                link.click();
            }})
            .catch(function(error) {{
                console.error('oops, something went wrong!', error);
                alert("Download failed. Please try again.");
            }});
        }}
    </script>
</body>
</html>
    """
    return html_content
