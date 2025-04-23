#!/usr/bin/env python3
import argparse
import requests
import sys
import os
import re
import curses
from collections import OrderedDict

try:
    from colorama import init, Fore, Style, Back
    init(autoreset=True)
    COLOR = True
except ImportError:
    COLOR = False

# Cores e estilos
def col(text, color, background=None, bold=False):
    if not COLOR: return text
    result = f"{color}{text}{Style.RESET_ALL}"
    if background:
        result = f"{background}{result}"
    if bold:
        result = f"{Style.BRIGHT}{result}"
    return result


def scan_url(url, patterns, extra_patterns=None, show_all=False):
    """
    Escaneia a URL procurando pelos padrões sensíveis.
    - patterns: padrões normais (sempre usados)
    - extra_patterns: padrões extras usados apenas quando show_all=True
    - show_all: se True, mostra todas as ocorrências e usa padrões extras
    """
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code != 200:
            return {'_error': [f'status {resp.status_code}']}
        content = resp.text
    except Exception as e:
        return {'_error': [str(e)]}

    # Se show_all, inclui os padrões extras
    active_patterns = patterns.copy()
    if show_all and extra_patterns:
        active_patterns.extend(extra_patterns)
    
    founds = OrderedDict()
    for pat in active_patterns:
        try:
            rx = re.compile(pat, re.IGNORECASE)
            matches = list(rx.finditer(content))
        except re.error:
            # Para padrões simples (não regex), faça uma busca direta
            if not pat.startswith(r"(?"):  # Provavelmente não é regex
                lower_content = content.lower()
                lower_pattern = pat.lower()
                matches = []
                start = 0
                while True:
                    index = lower_content.find(lower_pattern, start)
                    if index == -1:
                        break
                    # Criar um objeto similar ao retorno de match
                    class SimpleMatch:
                        def __init__(self, start, end, text):
                            self.start_pos = start
                            self.end_pos = end
                            self.matched_text = text
                        def start(self): return self.start_pos
                        def end(self): return self.end_pos
                        def group(self, group_num=0): return self.matched_text
                    
                    end = index + len(lower_pattern)
                    matched_text = content[index:end]
                    matches.append(SimpleMatch(index, end, matched_text))
                    start = end
            else:
                matches = []
        
        snippets = []
        for m in matches:
            start, end = m.start(), m.end()
            snippet = content[max(0, start-50):min(len(content), end+50)]
            snippet = snippet.replace("\n", " ").strip()
            # destaque match
            snippet = snippet[:start-max(0, start-50)] + col(m.group(0), Fore.YELLOW, bold=True) + snippet[end-max(0, start-50):]
            # Verifica se deve mostrar todas as ocorrências ou apenas as únicas
            if show_all or snippet not in snippets:
                snippets.append(snippet)
            if not show_all and len(snippets) >= 5:
                break
        if snippets:
            founds[pat] = snippets
    return founds


def layout_textual(results, show_all=False):
    sep = col('━'*80, Fore.CYAN)
    for url, data in results.items():
        print(col(f"┏━━ URL: {url}", Fore.GREEN, bold=True))
        print(sep)
        if '_error' in data:
            print(col(f"⚠ Erro: {data['_error'][0]}", Fore.RED))
        elif not data:
            print(col("✔ Nenhuma ocorrência sensível.", Fore.GREEN))
        else:
            for pat, snips in data.items():
                # Destaque especial para diferentes tipos de padrões
                if pat.startswith(r"(?"):  # É um regex complexo
                    pattern_style = col(f"🔍 Padrão: {pat}", Fore.MAGENTA, bold=True)
                else:  # É uma palavra-chave simples
                    pattern_style = col(f"👁 Palavra-chave: {pat}", Fore.BLUE, bold=True)
                
                print("\n" + pattern_style)
                print(col('─'*70, Fore.CYAN))
                
                for i, s in enumerate(snips):
                    # Numerar cada ocorrência para facilitar a leitura
                    print(f"{col(f'  {i+1}.', Fore.WHITE, bold=True)} {s}")
                    # Adicionar uma linha entre as ocorrências se --all estiver ativo
                    if show_all and i < len(snips) - 1:
                        print(col('  ' + '· '*30, Fore.CYAN))
        print(f"\n{sep}\n")


def visual_menu(results, show_all=False):
    def main(stdscr):
        curses.use_default_colors()
        curses.start_color()
        curses.init_pair(1, curses.COLOR_GREEN, -1)  # URLs
        curses.init_pair(2, curses.COLOR_CYAN, -1)   # Separadores
        curses.init_pair(3, curses.COLOR_RED, -1)    # Erros
        curses.init_pair(4, curses.COLOR_MAGENTA, -1)  # Padrões
        curses.init_pair(5, curses.COLOR_YELLOW, -1)   # Matches
        curses.init_pair(6, curses.COLOR_BLUE, -1)     # Palavras-chave simples
        curses.init_pair(7, curses.COLOR_WHITE, curses.COLOR_BLUE)  # Seleção
        
        curses.curs_set(0)
        stdscr.keypad(True)
        urls = list(results.keys())
        idx = 0
        viewing = False
        offset = 0
        pattern_idx = 0
        pattern_offset = 0
        current_patterns = []
        
        while True:
            stdscr.clear()
            h, w = stdscr.getmaxyx()
            
            # Menu de URLs
            if not viewing:
                stdscr.addstr(0, 0, "URLs Escaneadas", curses.A_BOLD)
                stdscr.addstr(1, 0, "↑/↓: Navegar | Enter: Ver detalhes | q: Sair", curses.color_pair(2))
                stdscr.addstr(2, 0, "─" * (w-1), curses.color_pair(2))
                
                for i, url in enumerate(urls[offset:offset + h - 4]):
                    if i + offset == idx:
                        stdscr.attron(curses.color_pair(7) | curses.A_BOLD)
                        stdscr.addstr(i+3, 0, f" {url} ".ljust(w-1))
                        stdscr.attroff(curses.color_pair(7) | curses.A_BOLD)
                    else:
                        stdscr.addstr(i+3, 0, f" {url}", curses.color_pair(1))
            
            # Visualização de resultados
            else:
                sel = urls[idx]
                data = results[sel]
                
                # Se é a primeira visualização, inicialize a lista de padrões
                if not current_patterns:
                    current_patterns = list(data.keys()) if data and '_error' not in data else []
                
                # Cabeçalho
                stdscr.addstr(0, 0, f"Resultados para: ", curses.A_BOLD)
                stdscr.addstr(f"{sel}", curses.color_pair(1) | curses.A_BOLD)
                stdscr.addstr(1, 0, "↑/↓: Navegar | b: Voltar | →: Próximo padrão | ←: Padrão anterior | q: Sair", curses.color_pair(2))
                stdscr.addstr(2, 0, "═" * (w-1), curses.color_pair(2))
                
                display = []
                
                if '_error' in data:
                    stdscr.addstr(3, 0, f"⚠ Erro: {data['_error'][0]}", curses.color_pair(3) | curses.A_BOLD)
                elif not data:
                    stdscr.addstr(3, 0, "✔ Nenhuma ocorrência sensível.", curses.color_pair(1) | curses.A_BOLD)
                else:
                    # Mostrar qual padrão está sendo visualizado (com contador)
                    current_pat = current_patterns[pattern_idx]
                    pat_count = f"[{pattern_idx+1}/{len(current_patterns)}]"
                    
                    # Formatação baseada no tipo de padrão
                    if current_pat.startswith("(?"):
                        stdscr.addstr(3, 0, f"🔍 Padrão {pat_count}: ", curses.color_pair(4) | curses.A_BOLD)
                    else:
                        stdscr.addstr(3, 0, f"👁 Palavra-chave {pat_count}: ", curses.color_pair(6) | curses.A_BOLD)
                    
                    stdscr.addstr(current_pat, curses.A_BOLD)
                    stdscr.addstr(4, 0, "─" * (w-1), curses.color_pair(2))
                    
                    # Mostrar ocorrências do padrão atual
                    snips = data[current_pat]
                    row = 5
                    for i, snip in enumerate(snips[pattern_offset:]):
                        if row + 3 >= h:  # Deixar espaço para a barra de status
                            break
                        
                        # Número da ocorrência
                        stdscr.addstr(row, 2, f"{i+pattern_offset+1}. ", curses.A_BOLD)
                        
                        # Texto com palavras destacadas
                        snip_parts = re.split(r'(\x1b\[33m.*?\x1b\[0m)', snip)
                        col_pos = 2 + len(f"{i+pattern_offset+1}. ")
                        
                        for part in snip_parts:
                            if part.startswith('\x1b[33m'):
                                # Remover os códigos ANSI
                                clean_text = re.sub(r'\x1b\[\d+m', '', part)
                                stdscr.addstr(row, col_pos, clean_text, curses.color_pair(5) | curses.A_BOLD)
                                col_pos += len(clean_text)
                            else:
                                # Controle para não exceder a largura da tela
                                remaining_width = w - col_pos - 1
                                if len(part) > remaining_width:
                                    part = part[:remaining_width-3] + "..."
                                
                                stdscr.addstr(row, col_pos, part)
                                col_pos += len(part)
                        
                        # Adicionar separador entre ocorrências se --all está ativo
                        row += 1
                        if show_all and i < len(snips) - 1:
                            stdscr.addstr(row, 2, "· " * ((w-4)//2), curses.color_pair(2))
                            row += 1
                        
                        # Adicionar linha em branco para melhor espaçamento
                        row += 1
                
                # Barra de status na parte inferior
                if len(current_patterns) > 0:
                    status = f"Padrão {pattern_idx+1}/{len(current_patterns)}"
                    if len(data.get(current_patterns[pattern_idx], [])) > 0:
                        status += f" | Ocorrências: {len(data[current_patterns[pattern_idx]])}"
                    stdscr.addstr(h-1, 0, status.ljust(w-1), curses.color_pair(2) | curses.A_REVERSE)
            
            stdscr.refresh()
            c = stdscr.getch()
            
            # Controles globais
            if c in (ord('q'), 27):  # q ou ESC
                break
            
            # Controles quando visualizando resultados
            if viewing:
                if c == ord('b'):  # Voltar para a lista de URLs
                    viewing = False
                    offset = 0
                    current_patterns = []
                    pattern_idx = 0
                    pattern_offset = 0
                elif c == curses.KEY_RIGHT and current_patterns:  # Próximo padrão
                    if pattern_idx < len(current_patterns) - 1:
                        pattern_idx += 1
                        pattern_offset = 0
                elif c == curses.KEY_LEFT and current_patterns:  # Padrão anterior
                    if pattern_idx > 0:
                        pattern_idx -= 1
                        pattern_offset = 0
                elif c == curses.KEY_DOWN and current_patterns:  # Rolar para baixo nas ocorrências
                    data = results[urls[idx]]
                    current_pat = current_patterns[pattern_idx]
                    if current_pat in data and pattern_offset < len(data[current_pat]) - 1:
                        pattern_offset += 1
                elif c == curses.KEY_UP and current_patterns:  # Rolar para cima nas ocorrências
                    if pattern_offset > 0:
                        pattern_offset -= 1
            
            # Controles no menu de URLs
            else:
                if c == curses.KEY_DOWN and idx < len(urls)-1:
                    idx += 1
                    if idx - offset >= h-4:
                        offset += 1
                elif c == curses.KEY_UP and idx > 0:
                    idx -= 1
                    if idx < offset:
                        offset -= 1
                elif c in (10, 13):  # Enter
                    viewing = True
                    pattern_idx = 0
                    pattern_offset = 0
                    current_patterns = []
    
    try:
        curses.wrapper(main)
    except Exception as e:
        print(f"Erro no modo visual: {e}")
        print("Voltando para modo texto...")
        layout_textual(results, show_all)


def main():
    parser = argparse.ArgumentParser(description='LinkZilla+Scan: detecta padrões sensíveis e exibe resultados bonitos.')
    parser.add_argument('-w','--wordlist', help='Arquivo com URLs')
    parser.add_argument('url', nargs='?', help='URL única')
    parser.add_argument('--visual', action='store_true', help='Menu interativo')
    parser.add_argument('--all', action='store_true', help='Mostra todas as ocorrências e padrões extras (mais genéricos)')
    parser.add_argument('-s','--sensitive', nargs='+', default=[
        r"(?i)(password|senha)\s*[:=]\s*['\"][^'\"]{4,}['\"]",
        r"(?i)(api[-_]?key|access[-_]?token|auth[-_]?token)\s*[:=]\s*['\"][A-Za-z0-9\-_]{10,}['\"]",
        r"(?i)jwt\s*[:=]\s*['\"][A-Za-z0-9\-_]+\.[A-Za-z0-9\-_]+\.[A-Za-z0-9\-_]+['\"]"
    ], help='Padrões sensíveis (regex)')
    args = parser.parse_args()

    # Padrões extras para quando --all está ativado
    # Estes são extraídos do segundo código (paste-2.txt)
    extra_patterns = [
        # Termos básicos em diversos idiomas
        "admin", "administrator", "administrateur", "amministratore", "root", "superuser",
        "password", "pwd", "credential",
        "senha", "administrador", "adm", "chave", "palavra-chave", "segredo",
        "contraseña", "clave", "secreto",
        "motdepasse", "clé",
        "passwort", "geheim", "benutzer", "schlüssel",
        "админ", "администратор", "пароль", "ключ",
        "管理员", "密码", "管理者", "密钥",
        "パスワード", "管理者", "秘密",
        "مدير", "كلمة السر", "كلمة المرور", "سر", "مفتاح",
        "segreto",
        "परशसक", "पसवरड", "गपत",
        "lösenord", "administratör", "hemlighet",
        "wachtwoord", "beheerder", "geheim",
        "hasło", "tajne",
        "şifre", "yönetici", "gizli", "anahtar",
        "مدیر", "رمز عبور", "کلید",
        # Variações com caracteres especiais
        "p@ssw0rd", "Adm1n", "s3nh4",
        # Padrão Slack
        r"(?i)xox[baprs]-[0-9]{12}-[0-9]{12}-[a-zA-Z0-9]{24}"
    ]

    urls = []
    if args.wordlist:
        if not os.path.isfile(args.wordlist): sys.exit('Arquivo não encontrado')
        with open(args.wordlist) as f: urls = [l.strip() for l in f if l.strip()]
    elif args.url:
        urls = [args.url]
    else:
        parser.print_help(); sys.exit(1)

    results = OrderedDict()
    for u in urls:
        results[u] = scan_url(u, args.sensitive, extra_patterns, args.all)

    print(col("╔══════════════════════╗", Fore.CYAN))
    print(col("║ UrlBandit By Thome07 ║", Fore.CYAN, bold=True))
    print(col("╚══════════════════════╝", Fore.CYAN))
    print(f"\n{col('✓ Modo', Fore.GREEN)} {'Visual' if args.visual else 'Textual'}")
    print(f"{col('✓ Modo Abrangente', Fore.GREEN)} {'Ativado' if args.all else 'Desativado'}")
    print(f"{col('✓ URLs para verificar', Fore.GREEN)} {len(urls)}")
    print()

    if args.visual:
        visual_menu(results, args.all)
    else:
        layout_textual(results, args.all)

if __name__ == '__main__':
    main()
