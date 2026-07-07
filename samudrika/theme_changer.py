import re

with open('frontend/index.html', 'r') as f:
    html = f.read()

# CSS changes
html = html.replace('background: radial-gradient(circle at 50% 50%, #0c1527 0%, #02040a 100%);', 'background: radial-gradient(circle at 50% 50%, #f9eac3 0%, #d4b882 100%);')
html = html.replace('rgba(15,23,42,0.9) 0%, rgba(2,6,23,0.95) 100%', 'rgba(255,255,255,0.7) 0%, rgba(245,235,210,0.85) 100%')
html = html.replace('text-gold {', 'text-theme-blue {')
html = html.replace('background: linear-gradient(to right, #fceabb, #f8b500);', 'color: #194b75;')
html = html.replace('-webkit-background-clip: text;', '')
html = html.replace('-webkit-text-fill-color: transparent;', '')
html = html.replace('rgba(248, 181, 0,', 'rgba(25, 75, 117,')

# Tailwind class replacements
html = html.replace('text-white', 'text-slate-900')
html = html.replace('bg-slate-950/80', 'bg-white/60')
html = html.replace('border-yellow-600/30', 'border-[#194b75]/30')
html = html.replace('border-yellow-600/40', 'border-[#194b75]/40')
html = html.replace('border-yellow-600/20', 'border-[#194b75]/20')
html = html.replace('text-yellow-500', 'text-[#194b75]')
html = html.replace('text-yellow-300', 'text-[#306c9e]')
html = html.replace('border-yellow-500', 'border-[#194b75]')
html = html.replace('bg-yellow-500/20', 'bg-[#194b75]/20')
html = html.replace('bg-yellow-600/10', 'bg-[#194b75]/10')
html = html.replace('focus:border-yellow-500', 'focus:border-[#194b75]')
html = html.replace('bg-black/40', 'bg-white/40')
html = html.replace('bg-black/90', 'bg-black/60')
html = html.replace('text-gray-400', 'text-slate-600')
html = html.replace('text-gray-300', 'text-slate-700')
html = html.replace('placeholder-gray-600', 'placeholder-slate-500')
html = html.replace('text-gold', 'text-theme-blue')
html = html.replace('btn-gold', 'btn-blue')
html = html.replace('bg-slate-950', 'bg-[#f4ebd8]')

# Change btn-gold CSS to btn-blue
html = html.replace('.btn-gold', '.btn-blue')
html = html.replace('background: linear-gradient(135deg, #f5af19 0%, #f12711 100%);', 'background: linear-gradient(135deg, #2b70a8 0%, #10304f 100%);')
html = html.replace('rgba(241, 39, 17, 0.4)', 'rgba(16, 48, 79, 0.4)')

# Increase version
html = html.replace('script.js?v=3', 'script.js?v=4')

with open('frontend/index.html', 'w') as f:
    f.write(html)
