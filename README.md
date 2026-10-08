# Informações Comerciais via WhatsApp

Serviço para consultar indicadores no SQL Server e enviá-los, em horário programado,
pela API oficial do WhatsApp Business Cloud.

## Estado inicial seguro

O arquivo `config.example.json` vem com `dry_run: true`. Nesse modo nenhuma mensagem é enviada:
o texto é apenas exibido no terminal e registrado em `data/envios.db`.

## Configuração

1. Copie `.env.example` para `.env` e preencha os dados da Meta.
2. Copie `config.example.json` para `config.json` e ajuste a conexão, a consulta, os destinatários e o texto. O `config.json` é local e não é publicado no GitHub.
3. Teste a configuração:

```powershell
python app.py --check
```

4. Execute uma vez em modo de teste:

```powershell
python app.py --run-once
```

5. Depois de validar a mensagem, altere `dry_run` para `false`.

O token nunca deve ser gravado no `config.json`. Mantenha-o somente no `.env` ou em
uma variável de ambiente protegida.

## Consulta SQL

A consulta deve retornar exatamente uma linha. Cada coluna vira uma variável do
modelo da mensagem. Exemplo:

```sql
SELECT
    CAST(GETDATE() AS date) AS data_referencia,
    CAST(SUM(VALOR) AS decimal(18,2)) AS valor_faturado,
    COUNT(*) AS quantidade_pedidos
FROM dbo.FATURAMENTO
WHERE DATA >= CAST(GETDATE() AS date)
  AND DATA < DATEADD(day, 1, CAST(GETDATE() AS date));
```

## Agendamento

O aplicativo executa uma vez e termina. Em produção, `python app.py --run-once` será
executado de segunda a sexta às 18h pelo Agendador de Tarefas do Windows. Isso facilita
reinício, auditoria e evita manter um processo permanentemente aberto.

A tarefa pode ser instalada com:

```powershell
powershell -ExecutionPolicy Bypass -File .\install_scheduled_task.ps1
```

Ela é executada com o usuário Windows que fez a instalação e grava os resultados em
`data/logs`. A configuração inicial usa logon interativo, portanto o usuário precisa
estar conectado ao Windows às 18h para que suas credenciais integradas alcancem o SQL
Server. Em um servidor, prefira uma conta de serviço com acesso somente leitura ao ERP.

## Painel administrativo local

O painel fica disponível somente neste computador em `http://127.0.0.1:8765/` e permite:

- consultar e editar o SELECT usado pela rotina;
- visualizar e editar o texto da mensagem;
- testar a consulta sem enviar WhatsApp;
- adicionar, pausar e excluir destinatários;
- consultar o histórico dos últimos 50 envios.

Para iniciar manualmente, execute `python dashboard.py`. Para iniciar automaticamente
ao entrar no Windows, execute uma vez:

```powershell
powershell -ExecutionPolicy Bypass -File .\install_dashboard_task.ps1
```

O arquivo `Abrir Painel DMB.ps1` abre o painel no navegador padrão.

## API do WhatsApp

Para disparos iniciados pela empresa, configure um template aprovado no WhatsApp
Manager. Os valores indicados em `template_parameters` são enviados na mesma ordem
dos campos variáveis `{{1}}`, `{{2}}` etc. do template.
