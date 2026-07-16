# 🏭 Short Factory — Guia rápido (Windows)

Guia passo a passo para rodar o app **na sua máquina** e produzir Shorts.
Você não precisa saber programar — é só seguir na ordem.

> Tempo estimado na primeira vez: ~15 min (a maior parte é instalação
> automática). Nas próximas, ~10 segundos.

---

## Passo 1 — Instalar os 3 programas necessários

Abra o **Prompt de Comando** (aperte a tecla Windows, digite `cmd`, Enter) e
cole os 3 comandos abaixo, **um de cada vez** (aperte Enter após cada um e
espere terminar):

```bat
winget install Python.Python.3.11
winget install OpenJS.NodeJS.LTS
winget install ffmpeg
```

- **Python** — roda o motor de vídeo.
- **Node.js** — roda o site.
- **ffmpeg** — monta o vídeo em si.

> Se `winget install ffmpeg` não achar, use: `winget install Gyan.FFmpeg`

⚠️ **IMPORTANTE:** depois de instalar, **feche o Prompt de Comando e o
navegador** (ou reinicie o PC). Isso faz o Windows "enxergar" os programas
recém-instalados. Sem isso, dá erro de "não reconhecido".

---

## Passo 2 — Baixar o projeto

**Opção A (mais fácil):** na página do repositório no GitHub, clique no botão
verde **`Code` → `Download ZIP`**, e extraia a pasta em algum lugar fácil (ex.:
`C:\Short-Factory`).

**Opção B (com git):**

```bat
git clone <URL-do-repositorio> C:\Short-Factory
```

---

## Passo 3 — Ligar o app (2 duplo-cliques)

Dentro da pasta do projeto, você verá dois arquivos:

1. **Dê duplo-clique em `start_backend.bat`**
   Uma janela preta abre e escreve `Backend rodando em http://localhost:8000`.
   Na primeira vez ela instala tudo sozinha (leva 1-2 min). **Deixe aberta.**

2. **Dê duplo-clique em `start_frontend.bat`**
   Outra janela preta abre e escreve `Frontend rodando em
   http://localhost:5173`. Na primeira vez ela instala o site (leva 1-2 min).
   **Deixe aberta.**

> As duas janelas pretas precisam ficar **abertas** enquanto você usa o app.
> Para desligar depois, é só fechá-las.

---

## Passo 4 — Abrir e usar

1. Abra o navegador em **http://localhost:5173**
2. Clique no preset **⭐ The Chapter — Short 1** (já vem com ordem, timing,
   hook, CTA e correções de legenda prontos).
3. Arraste as **13 imagens** (nomes tipo `0_00`, `0_04`, … `0_44`), o **MP3** da
   narração e o **SRT** das legendas.
   → A ordem e os tempos se ajustam sozinhos (inclusive `0_26` antes de `0_20`).
4. Confira no passo **Preview** (a barra deve ficar verde).
5. Clique em **🎬 Gerar Short**, espere a barra chegar a 100% e clique em
   **⬇ Baixar mp4**.

Pronto — seu Short está na pasta de Downloads. ✅

---

## Solução de problemas (os 3 erros mais comuns)

### 1. `'ffmpeg' não é reconhecido...` (ou `'python'`, ou `'npm'`)
O Windows ainda não enxerga o programa recém-instalado.
- **Feche as janelas pretas e o navegador e ABRA de novo** os `.bat`.
- Se persistir, **reinicie o PC** e tente de novo.
- Confirme que o programa instalou: no `cmd`, rode `ffmpeg -version`.

### 2. `address already in use` / porta 8000 ou 5173 ocupada
Já tem algo usando a porta (talvez o app aberto duas vezes).
- Feche **todas** as janelas pretas do Short Factory e abra os `.bat` de novo.
- Se ainda ocupar, reinicie o PC (garante que nada ficou preso).
- Para trocar a porta do backend, edite `start_backend.bat` e mude `--port 8000`
  para `--port 8001` (e avise, que aí ajustamos o proxy do frontend).

### 3. PowerShell bloqueia o `npm` (erro de "execução de scripts foi desabilitada")
Acontece em alguns Windows por política de segurança.
- Abra o **PowerShell como Administrador** (tecla Windows, digite `powershell`,
  clique com o botão direito → *Executar como administrador*) e rode:

  ```powershell
  Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
  ```

  Digite `S` (ou `Y`) e Enter. Depois feche e abra o `start_frontend.bat` de
  novo.

---

## Checklist do gate P0 (para o teste do Short 1)

- [ ] Segui o QUICKSTART e o app abriu em http://localhost:5173
- [ ] Usei o preset ⭐ The Chapter — Short 1
- [ ] Subi as 13 imagens + MP3 + SRT reais
- [ ] Preview ficou verde (cobre o áudio, tempos crescentes)
- [ ] Gerei e baixei o mp4 (1080×1920, ~47,7s)
- [ ] Legenda saiu com "Ronald Read" corrigido, hook no início e CTA no fim
- [ ] Cronometrei o trabalho humano: **< 10 min** ✅
- [ ] Vídeo no mesmo padrão do que eu montava no CapCut

Bateu tudo? **O gate P0 está aberto** — o app vira sua linha de produção. 🏭✅
