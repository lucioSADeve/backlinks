# Backlinks Checker

Script automatizado para verificação de backlinks usando SEOPack e SEMrush.

## Configuração

1. Crie um repositório no GitHub
2. Faça upload dos arquivos do projeto
3. Configure as secrets no GitHub:
   - Vá em Settings > Secrets and variables > Actions
   - Adicione as seguintes secrets:
     - `SEOPACK_LOGIN`: Seu usuário do SEOPack
     - `SEOPACK_PASSWORD`: Sua senha do SEOPack

## Como usar

1. Adicione os domínios que deseja verificar no arquivo `domains.txt`, um por linha
2. O script rodará automaticamente a cada 6 horas
3. Para rodar manualmente:
   - Vá em Actions no GitHub
   - Selecione o workflow "Backlinks Checker"
   - Clique em "Run workflow"

## Resultados

- Os arquivos de backlinks serão salvos na pasta `Google Drive`
- Em caso de erros, screenshots serão salvos na pasta `debug`
- Os resultados podem ser baixados na seção "Artifacts" de cada execução

## Observações

- O script remove automaticamente os domínios da lista após processá-los com sucesso
- Se houver erro em um domínio, ele permanecerá na lista para ser processado na próxima execução
- Os arquivos são salvos com timestamp e nome do domínio para evitar sobrescrita 