IMPLANTAÇÃO NO SRV-APP-01
=========================

1. Copie toda a pasta do projeto para o servidor usando a sessão RDP.
2. Abra o PowerShell como administrador.
3. Execute primeiro:

   powershell -ExecutionPolicy Bypass -File ".\deployment\Verificar Servidor.ps1"

4. Não execute os instaladores das tarefas antes de validar o diagnóstico.

O arquivo .env contém o token da Meta e deve permanecer restrito aos
administradores e à futura conta de serviço. Não envie esse arquivo por e-mail
ou aplicativos de mensagens.

Destino recomendado após a validação:

   C:\Apps\RoboDMBWhatsApp
