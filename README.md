# URLBandit
URLBandit é uma ferramenta de escaneamento de URLs que busca por padrões sensíveis em páginas web. O script permite analisar múltiplas URLs para identificar vulnerabilidades, dados sensíveis ou outras informações expostas acidentalmente, usando padrões predefinidos ou customizados.

### Funcionalidades
Padrão: Chama a ferramenta com uma URL para realizar a auditoria.

-w <wordlist>: Passa uma wordlist de URLs para testar múltiplas rotas ou pontos de entrada do site.

--visual: Torna a saída mais interativa e fácil de visualizar, criando um menu interativo para navegar pelos resultados.

--all: Exibe palavras sensíveis que aparecem frequentemente em sites, como "root" ou "admin", que podem indicar áreas críticas ou vulnerabilidades.

### Como Usar

Clone o repositório:
``git clone https://github.com/Thome07/urlBandit``

Navegue até o diretório do projeto:
``cd nome-do-repositorio``

Para executar a ferramenta, use o comando:
``python3 urlbandit <URL>``

Para utilizar uma wordlist de URLs:
``python3 urlbandit -w <wordlist>``

Para exibir os resultados de forma interativa:
``python3 urlbandit <URL> --visual``

Para mostrar palavras sensíveis no site:
``python3 urlbandit <URL> --all``
