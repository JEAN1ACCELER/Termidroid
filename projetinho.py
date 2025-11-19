import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import random


# Constantes (Vcs realmente leem isso?)
BLOCK_SIZE = 30  # Tamanho visual de cada bloco em pixels
BLOCK_PADDING = 5    # Espaçamento entre os blocos
GRID_COLS = 16       # Número de colunas no disco
GRID_ROWS = 8        # Número de linhas no disco
TOTAL_BLOCKS = GRID_COLS * GRID_ROWS


# Cores
COLOR_FREE = "#d3d3d3"
COLOR_INDEX_BLOCK = "#8E44AD" # Roxo para blocos de índice (Inode)


class FileSystem:
    """
    Classe que gerencia a lógica do sistema de arquivos simulado.
    """
    def __init__(self, num_blocks):
        self.num_blocks = num_blocks
        # self.blocks armazena o nome do arquivo que ocupa o bloco, ou None se estiver livre
        self.blocks = [None] * num_blocks
       
        # self.fat simula a Tabela de Alocação de Arquivos (para alocação encadeada)
        # O índice é o bloco atual, o valor é o próximo bloco. -1 é fim de arquivo (EOF).
        self.fat = [0] * num_blocks  # 0 = livre/disponível
       
        # self.index_table simula uma tabela de inodes (para alocação indexada)
        # Mapeia: {num_bloco_indice -> [lista_blocos_de_dados]}
        self.index_table = {}
       
        # self.files armazena metadados dos arquivos criados
        self.files = {}  
        # Ex Contíguo: {'nome': {'size': 5, 'method': 'contiguous', 'blocks': [0,1,2,3,4]}}
        # Ex Encadeado: {'nome2': {'size': 3, 'method': 'linked', 'start': 7, 'blocks': [7, 10, 11]}}
        # Ex Indexado: {'nome3': {'size': 3, 'method': 'indexed', 'index_block': 20, 'data_blocks': [2, 5, 8]}}


    def find_free_blocks_contiguous(self, size):
        """Encontra um espaço contíguo de 'size' blocos livres."""
        # ... (código existente) ...
        count = 0
        start_index = -1
        for i in range(self.num_blocks):
            if self.blocks[i] is None:
                if count == 0:
                    start_index = i
                count += 1
                if count == size:
                    return list(range(start_index, start_index + size))
            else:
                count = 0
                start_index = -1
        return None


    def allocate_contiguous(self, file_name, file_size):
        """Aloca um arquivo usando o método contíguo."""
        # ... (código existente) ...
        if file_name in self.files:
            return False, "Nome de arquivo já existe."
        if file_size <= 0:
            return False, "Tamanho do arquivo deve ser positivo."


        block_list = self.find_free_blocks_contiguous(file_size)
       
        if block_list:
            for block in block_list:
                self.blocks[block] = file_name
           
            self.files[file_name] = {
                'size': file_size,
                'method': 'contiguous',
                'blocks': block_list
            }
            return True, "Arquivo alocado com sucesso."
        else:
            return False, "Espaço contíguo insuficiente (Fragmentação Externa)."


    def find_free_block(self, start_from=0):
        """Encontra o próximo bloco livre no disco."""
        # ... (código existente) ...
        for i in range(start_from, self.num_blocks):
            if self.blocks[i] is None:
                return i
        for i in range(0, start_from): # Tenta do início
             if self.blocks[i] is None:
                return i
        return -1 # Disco cheio


    def get_free_blocks_count(self):
        """Retorna o número de blocos livres."""
        return self.blocks.count(None)


    def allocate_linked(self, file_name, file_size):
        """Aloca um arquivo usando o método encadeado (FAT)."""
        # ... (código existente) ...
        if file_name in self.files:
            return False, "Nome de arquivo já existe."
        if file_size <= 0:
            return False, "Tamanho do arquivo deve ser positivo."


        # Verifica se há blocos livres suficientes (não precisam ser contíguos)
        if self.get_free_blocks_count() < file_size:
            return False, "Espaço insuficiente no disco."


        # Alocação
        block_list = []
        current_block = -1
       
        for _ in range(file_size):
            free_block = self.find_free_block(current_block + 1)
            # Não deve falhar, pois verificamos o espaço total
           
            self.blocks[free_block] = file_name
            block_list.append(free_block)
           
            if current_block != -1:
                self.fat[current_block] = free_block # Aponta o bloco anterior para este
           
            current_block = free_block


        self.fat[current_block] = -1 # Marca o fim do arquivo (EOF)
       
        self.files[file_name] = {
            'size': file_size,
            'method': 'linked',
            'start': block_list[0],
            'blocks': block_list # Armazena para facilitar a visualização e deleção
        }
        return True, "Arquivo alocado com sucesso."


    def allocate_indexed(self, file_name, file_size):
        """Aloca um arquivo usando o método indexado (Inode)."""
        if file_name in self.files:
            return False, "Nome de arquivo já existe."
        if file_size <= 0:
            return False, "Tamanho do arquivo deve ser positivo."


        # Precisa de 'file_size' blocos de dados + 1 bloco de índice
        if self.get_free_blocks_count() < (file_size + 1):
             return False, "Espaço insuficiente no disco (precisa de blocos de dados + 1 bloco de índice)."
       
        # 1. Encontra e aloca o bloco de índice
        index_block = self.find_free_block()
        if index_block == -1: # Não deve acontecer
             return False, "Erro ao alocar bloco de índice."
       
        self.blocks[index_block] = file_name # Marca como ocupado pelo arquivo


        # 2. Encontra e aloca os blocos de dados
        data_blocks = []
        for _ in range(file_size):
            data_block = self.find_free_block(index_block + 1) # Procura a partir do próximo
            if data_block == -1:
                 # Se ficar sem espaço no meio, desfaz a alocação
                 self.blocks[index_block] = None
                 for b in data_blocks:
                     self.blocks[b] = None
                 return False, "Erro inesperado ao alocar blocos de dados."
           
            self.blocks[data_block] = file_name
            data_blocks.append(data_block)
            index_block = data_block # Otimiza a próxima busca
       
        # 3. Registra na tabela de inodes e nos metadados do arquivo
        self.index_table[index_block] = data_blocks
       
        self.files[file_name] = {
            'size': file_size,
            'method': 'indexed',
            'index_block': index_block,
            'data_blocks': data_blocks
        }
        return True, "Arquivo alocado com sucesso."




    def delete_file(self, file_name):
        """Deleta um arquivo do sistema."""
        # ... (código existente) ...
        if file_name not in self.files:
            return False, "Arquivo não encontrado."


        file_info = self.files[file_name]
       
        if file_info['method'] == 'contiguous':
            for block in file_info['blocks']:
                self.blocks[block] = None
       
        elif file_info['method'] == 'linked':
            # Percorre a cadeia da FAT para deletar
            current_block = file_info['start']
            while current_block != -1:
                next_block = self.fat[current_block]
                self.blocks[current_block] = None
                self.fat[current_block] = 0 # Limpa entrada da FAT
                current_block = next_block
       
        elif file_info['method'] == 'indexed':
            index_block = file_info['index_block']
            data_blocks = file_info['data_blocks']
           
            # Libera blocos de dados
            for block in data_blocks:
                self.blocks[block] = None
               
            # Libera bloco de índice
            self.blocks[index_block] = None
           
            # Remove da tabela de inodes
            if index_block in self.index_table:
                del self.index_table[index_block]
       
        del self.files[file_name]
        return True, "Arquivo deletado com sucesso."


class App:
    """
    Classe principal da aplicação Tkinter.
    """
    def __init__(self, root):
        self.root = root
        self.root.title("Simulador de Gerenciamento de Arquivos")
        self.root.geometry("1300x700") # Janela maior
       
        self.fs = FileSystem(TOTAL_BLOCKS)
        self.file_colors = {} # Mapeia nome de arquivo para uma cor


        self.create_widgets()
        self.update_info_panels()
        self.draw_disk_blocks()


    def get_random_color(self):
        """Gera uma cor hexadecimal aleatória e legível."""
        # ... (código existente) ...
        r = random.randint(100, 250)
        g = random.randint(100, 250)
        b = random.randint(100, 250)
        return f'#{r:02x}{g:02x}{b:02x}'


    def create_widgets(self):
        """Cria os componentes da UI."""
       
        # --- Frame de Controle (Esquerda) ---
        control_frame = ttk.Frame(self.root, padding=10, width=300)
        control_frame.pack(side=tk.LEFT, fill=tk.Y)
        control_frame.pack_propagate(False) # Impede que o frame encolha
       
        ttk.Label(control_frame, text="Simulador de Alocação de Disco", font=("Arial", 16)).pack(pady=10)
       
        # --- Seção Criar Arquivo ---
        create_frame = ttk.LabelFrame(control_frame, text="Criar Arquivo", padding=10)
        create_frame.pack(fill=tk.X, pady=10)


        # ... (código existente) ...
        ttk.Label(create_frame, text="Nome:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
        self.entry_file_name = ttk.Entry(create_frame, width=20)
        self.entry_file_name.grid(row=0, column=1, sticky=tk.W, padx=5, pady=2)


        ttk.Label(create_frame, text="Tamanho (blocos):").grid(row=1, column=0, sticky=tk.W, padx=5, pady=2)
        self.spin_file_size = ttk.Spinbox(create_frame, from_=1, to=TOTAL_BLOCKS, width=5)
        self.spin_file_size.grid(row=1, column=1, sticky=tk.W, padx=5, pady=2)


        ttk.Label(create_frame, text="Método:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=2)
        self.alloc_method = tk.StringVar(value="contiguous")
        ttk.Radiobutton(create_frame, text="Contígua", variable=self.alloc_method, value="contiguous").grid(row=2, column=1, sticky=tk.W, padx=5)
        ttk.Radiobutton(create_frame, text="Encadeada (FAT)", variable=self.alloc_method, value="linked").grid(row=3, column=1, sticky=tk.W, padx=5)
        # Novo Radiobutton para Indexada
        ttk.Radiobutton(create_frame, text="Indexada (Inode)", variable=self.alloc_method, value="indexed").grid(row=4, column=1, sticky=tk.W, padx=5)
       
        ttk.Button(create_frame, text="Criar Arquivo", command=self.on_create_file).grid(row=5, column=0, columnspan=2, pady=10)


        # --- Seção Gerenciar Arquivos ---
        manage_frame = ttk.LabelFrame(control_frame, text="Arquivos no Disco", padding=10)
        manage_frame.pack(fill=tk.BOTH, expand=True, pady=10)
       
        # ... (código existente) ...
        self.file_listbox = tk.Listbox(manage_frame)
        self.file_listbox.pack(fill=tk.BOTH, expand=True, side=tk.TOP)
       
        self.file_listbox.bind('<<ListboxSelect>>', self.on_file_select)
       
        ttk.Button(manage_frame, text="Deletar Selecionado", command=self.on_delete_file).pack(pady=10)
       
        self.label_file_info = ttk.Label(manage_frame, text="Selecione um arquivo para ver detalhes", wraplength=280, justify=tk.LEFT)
        self.label_file_info.pack(side=tk.BOTTOM, fill=tk.X)


        # --- Frame do Disco (Meio) ---
        disk_frame = ttk.Frame(self.root, padding=10)
        disk_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)


        self.canvas = tk.Canvas(disk_frame, bg="#ffffff")
        self.canvas.pack(fill=tk.BOTH, expand=True)
       
        # Bind para redimensionar o canvas
        self.canvas.bind("<Configure>", lambda e: self.draw_disk_blocks(self.get_selected_file()))


        # --- Frame de Informações (Direita) ---
        self.info_frame = ttk.Frame(self.root, padding=10, width=300)
        self.info_frame.pack(side=tk.RIGHT, fill=tk.Y)
        self.info_frame.pack_propagate(False)
       
        self.create_info_panel(self.info_frame)


    def create_info_panel(self, parent):
        """Cria o painel de abas com FAT, Inodes e Estatísticas."""
        notebook = ttk.Notebook(parent)
        notebook.pack(fill=tk.BOTH, expand=True)
       
        # --- Aba 1: Visualização da FAT ---
        fat_tab = ttk.Frame(notebook)
        notebook.add(fat_tab, text="Tabela FAT")
       
        fat_frame = ttk.Frame(fat_tab, padding=5)
        fat_frame.pack(fill=tk.BOTH, expand=True)
       
        ttk.Label(fat_frame, text="Índice: Valor (Próx. Bloco)").pack()
       
        cols = ('Bloco', 'Valor')
        self.fat_view = ttk.Treeview(fat_frame, columns=cols, show='headings', height=10)
        for col in cols:
            self.fat_view.heading(col, text=col)
            self.fat_view.column(col, width=60, anchor=tk.CENTER)
       
        vsb_fat = ttk.Scrollbar(fat_frame, orient="vertical", command=self.fat_view.yview)
        self.fat_view.configure(yscrollcommand=vsb_fat.set)
       
        vsb_fat.pack(side=tk.RIGHT, fill=tk.Y)
        self.fat_view.pack(fill=tk.BOTH, expand=True)
       
        # --- Aba 2: Tabela de Inodes ---
        inode_tab = ttk.Frame(notebook)
        notebook.add(inode_tab, text="Inodes")
       
        inode_frame = ttk.Frame(inode_tab, padding=5)
        inode_frame.pack(fill=tk.BOTH, expand=True)
       
        ttk.Label(inode_frame, text="Bloco de Índice -> [Blocos de Dados]").pack()
       
        cols_inode = ('Índice', 'Blocos de Dados')
        self.inode_view = ttk.Treeview(inode_frame, columns=cols_inode, show='headings', height=10)
        self.inode_view.heading('Índice', text='Índice')
        self.inode_view.column('Índice', width=50, anchor=tk.CENTER)
        self.inode_view.heading('Blocos de Dados', text='Blocos de Dados')
        self.inode_view.column('Blocos de Dados', width=150)
       
        vsb_inode = ttk.Scrollbar(inode_frame, orient="vertical", command=self.inode_view.yview)
        self.inode_view.configure(yscrollcommand=vsb_inode.set)
       
        vsb_inode.pack(side=tk.RIGHT, fill=tk.Y)
        self.inode_view.pack(fill=tk.BOTH, expand=True)


        # --- Aba 3: Estatísticas ---
        stats_tab = ttk.Frame(notebook)
        notebook.add(stats_tab, text="Estatísticas")
       
        stats_frame = ttk.Frame(stats_tab, padding=20)
        stats_frame.pack(fill=tk.BOTH, expand=True)
       
        self.label_total_space = ttk.Label(stats_frame, text="Espaço Total: ...", font=("Arial", 12))
        self.label_total_space.pack(anchor=tk.W, pady=5)
       
        self.label_used_space = ttk.Label(stats_frame, text="Espaço Usado: ...", font=("Arial", 12))
        self.label_used_space.pack(anchor=tk.W, pady=5)
       
        self.label_free_space = ttk.Label(stats_frame, text="Espaço Livre: ...", font=("Arial", 12))
        self.label_free_space.pack(anchor=tk.W, pady=5)


    def update_info_panels(self):
        """Atualiza todas as abas de informação."""
        self.update_fat_view()
        self.update_inode_view()
        self.update_stats_view()


    def update_fat_view(self):
        """Atualiza a Treeview da Tabela FAT."""
        self.fat_view.delete(*self.fat_view.get_children())
        for i, val in enumerate(self.fs.fat):
            if val != 0: # Mostra apenas entradas não-livres
                tag = 'eof' if val == -1 else ''
                self.fat_view.insert('', tk.END, values=(i, val), tags=(tag,))
        self.fat_view.tag_configure('eof', background='#FFC107') # Destaca EOF


    def update_inode_view(self):
        """Atualiza a Treeview da Tabela de Inodes."""
        self.inode_view.delete(*self.inode_view.get_children())
        for index_block, data_blocks in self.fs.index_table.items():
            data_str = ", ".join(map(str, data_blocks))
            self.inode_view.insert('', tk.END, values=(index_block, data_str))
           
    def update_stats_view(self):
        """Atualiza as estatísticas do disco."""
        total = self.fs.num_blocks
        free = self.fs.get_free_blocks_count()
        used = total - free
       
        self.label_total_space.config(text=f"Espaço Total: {total} blocos")
        self.label_used_space.config(text=f"Espaço Usado: {used} blocos")
        self.label_free_space.config(text=f"Espaço Livre: {free} blocos")


    def on_create_file(self):
        """Callback do botão 'Criar Arquivo'."""
        # ... (código existente) ...
        file_name = self.entry_file_name.get()
        try:
            file_size = int(self.spin_file_size.get())
        except ValueError:
            messagebox.showerror("Erro", "Tamanho do arquivo deve ser um número.")
            return


        if not file_name:
            messagebox.showerror("Erro", "Nome do arquivo não pode ser vazio.")
            return


        method = self.alloc_method.get()
        success = False
        message = ""


        if method == "contiguous":
            success, message = self.fs.allocate_contiguous(file_name, file_size)
        elif method == "linked":
            success, message = self.fs.allocate_linked(file_name, file_size)
        elif method == "indexed":
            success, message = self.fs.allocate_indexed(file_name, file_size)


        if success:
            if file_name not in self.file_colors:
                self.file_colors[file_name] = self.get_random_color()
            messagebox.showinfo("Sucesso", message)
            self.update_file_list()
            self.update_info_panels() # Atualiza FAT, Inodes e Stats
            self.draw_disk_blocks()
            self.entry_file_name.delete(0, tk.END) # Limpa o campo
        else:
            messagebox.showerror("Erro de Alocação", message)


    def on_delete_file(self):
        """Callback do botão 'Deletar Selecionado'."""
        # ... (código existente) ...
        file_name = self.get_selected_file()
        if not file_name:
            messagebox.showerror("Erro", "Selecione um arquivo para deletar.")
            return


        success, message = self.fs.delete_file(file_name)
       
        if success:
            messagebox.showinfo("Sucesso", message)
            if file_name in self.file_colors:
                del self.file_colors[file_name] # Remove a cor
            self.update_file_list()
            self.update_info_panels() # Atualiza FAT, Inodes e Stats
            self.draw_disk_blocks()
            self.label_file_info.config(text="Selecione um arquivo para ver detalhes")
        else:
            messagebox.showerror("Erro", message)


    def update_file_list(self):
        """Atualiza a Listbox com os arquivos do sistema."""
        # ... (código existente) ...
        self.file_listbox.delete(0, tk.END)
        for file_name in sorted(self.fs.files.keys()):
            self.file_listbox.insert(tk.END, file_name)


    def get_selected_file(self):
        """Retorna o nome do arquivo selecionado na listbox, ou None."""
        try:
            selected_index = self.file_listbox.curselection()[0]
            return self.file_listbox.get(selected_index)
        except IndexError:
            return None


    def on_file_select(self, event=None):
        """Mostra informações do arquivo quando selecionado na lista."""
        # ... (código existente) ...
        file_name = self.get_selected_file()
        if not file_name:
            return


        info = self.fs.files.get(file_name)
        if not info:
            return
           
        text = f"Arquivo: {file_name}\n"
        text += f"Tamanho: {info['size']} blocos\n"
        text += f"Método: {info['method']}\n"
       
        if info['method'] == 'contiguous':
            text += f"Blocos: {info['blocks']}"
       
        elif info['method'] == 'linked':
            text += f"Início: Bloco {info['start']}\n"
            # Monta a cadeia para exibição
            chain = []
            curr = info['start']
            while curr != -1:
                chain.append(str(curr))
                curr = self.fs.fat[curr]
            text += f"Cadeia: {' -> '.join(chain)} (EOF)"
           
        elif info['method'] == 'indexed':
            text += f"Bloco de Índice: {info['index_block']}\n"
            text += f"Blocos de Dados: {info['data_blocks']}"


        self.label_file_info.config(text=text)
        self.draw_disk_blocks(highlight_file=file_name) # Redesenha com destaque


    def draw_disk_blocks(self, highlight_file=None):
        """Desenha a grade de blocos do disco no canvas."""
        # ... (código existente, com modificações) ...
        self.canvas.delete("all")
       
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
       
        if canvas_width < 50 or canvas_height < 50: # Evita desenhar se o canvas for muito pequeno
            return
       
        # Ajusta o tamanho do bloco para caber no canvas
        block_w = (canvas_width - (GRID_COLS * BLOCK_PADDING)) / GRID_COLS
        block_h = (canvas_height - (GRID_ROWS * BLOCK_PADDING)) / GRID_ROWS
        block_size = max(5, min(block_w, block_h)) # Garante um tamanho mínimo


        # Informações do arquivo destacado
        highlight_info = self.fs.files.get(highlight_file)
       
        for i in range(TOTAL_BLOCKS):
            row = i // GRID_COLS
            col = i % GRID_COLS
           
            x0 = col * (block_size + BLOCK_PADDING) + BLOCK_PADDING
            y0 = row * (block_size + BLOCK_PADDING) + BLOCK_PADDING
            x1 = x0 + block_size
            y1 = y0 + block_size


            file_name = self.fs.blocks[i]
            color = COLOR_FREE
            outline_color = "#666"
            outline_width = 1


            if file_name:
                is_index_block = i in self.fs.index_table
                color = COLOR_INDEX_BLOCK if is_index_block else self.file_colors.get(file_name, "#FF0000")
               
                if file_name == highlight_file:
                    outline_color = "#0000FF" # Azul para destaque
                    outline_width = 3
           
            self.canvas.create_rectangle(x0, y0, x1, y1, fill=color, outline=outline_color, width=outline_width, tags=f"block_{i}")
           
            font_size = max(5, int(block_size / 3.5))
            self.canvas.create_text(x0 + block_size/2, y0 + block_size/2, text=str(i), fill="#333", font=("Arial", font_size))


            # Desenha setas de destaque
            if highlight_info:
                method = highlight_info['method']
               
                # Seta para método ENCADEADO
                if method == 'linked':
                    next_block = self.fs.fat[i]
                    if next_block != 0 and next_block != -1 and i in highlight_info['blocks']:
                        self.draw_arrow(i, next_block, block_size)


                # Setas para método INDEXADO
                elif method == 'indexed':
                    index_block = highlight_info['index_block']
                    data_blocks = highlight_info['data_blocks']
                   
                    if i == index_block:
                        # Desenha seta do bloco de índice para todos os blocos de dados
                        for data_block in data_blocks:
                            self.draw_arrow(index_block, data_block, block_size, color="#8E44AD")


    def draw_arrow(self, block_from, block_to, block_size, color="#0000FF"):
        """Desenha uma seta do centro do bloco_from para o centro do bloco_to."""
        # Centro do bloco de origem
        row_from = block_from // GRID_COLS
        col_from = block_from % GRID_COLS
        x_from = col_from * (block_size + BLOCK_PADDING) + BLOCK_PADDING + block_size / 2
        y_from = row_from * (block_size + BLOCK_PADDING) + BLOCK_PADDING + block_size / 2
       
        # Centro do bloco de destino
        row_to = block_to // GRID_COLS
        col_to = block_to % GRID_COLS
        x_to = col_to * (block_size + BLOCK_PADDING) + BLOCK_PADDING + block_size / 2
        y_to = row_to * (block_size + BLOCK_PADDING) + BLOCK_PADDING + block_size / 2
       
        self.canvas.create_line(x_from, y_from, x_to, y_to, arrow=tk.LAST, fill=color, width=2)




if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    root.mainloop()

