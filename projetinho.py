  function cmdStat(args) {
            if (args.length === 0) {
                printOutput('Uso: stat <nome_do_arquivo>', 'output-error');
                return;
            }
            
            const file = disk.files[args[0]];
            if (!file) {
                printOutput(`stat: ${args[0]}: Arquivo não encontrado`, 'output-error');
                return;
            }
            
            printOutput(`Estatísticas do arquivo: ${file.name}`, 'output-info');
            printOutput(`────────────────────────────────────────`);
            printOutput(`Tamanho: ${file.size} blocos (${file.size * 512} bytes)`);
            printOutput(`Método de alocação: ${disk.method}`);
            printOutput(`Blocos alocados: [${file.blocks.join(', ')}]`);
            printOutput(`Total de blocos: ${file.blocks.length}`);
            
            if (disk.method === 'encadeada') {
                printOutput(`Primeiro bloco: ${file.blocks[0]}`);
                printOutput(`Último bloco: ${file.blocks[file.blocks.length - 1]}`);
                printOutput(`Ponteiros FAT: ${file.blocks.slice(0, -1).map((block, i) => 
                    `${block}→${file.blocks[i+1]}`).join(', ')}`);
            } else if (disk.method === 'contigua') {
                printOutput(`Bloco inicial: ${file.blocks[0]}`);
                printOutput(`Blocos contíguos: ${file.blocks[0]} a ${file.blocks[0] + file.blocks.length - 1}`);
            } else if (disk.method === 'indexada') {
                printOutput(`Bloco de índice: ${file.indexBlock}`);
                printOutput(`Entradas no índice: ${file.blocks.length}`);
            }
            
            const fragmentation = calculateFragmentation(file);
            printOutput(`Fragmentação: ${fragmentation}%`);
        }
        
        function cmdClear() {
            document.getElementById('terminalOutput').innerHTML = '';
        }
        
        function cmdFormat() {
            if (Object.keys(disk.files).length > 0) {
                printOutput('Atenção: Todos os arquivos serão perdidos!', 'output-error');
                printOutput('Digite "format --force" para confirmar.');
                return;
            }
            
            if (commandHistory[commandHistory.length - 1] === 'format --force') {
                formatDiskInternal();
                printOutput('✓ Disco formatado com sucesso', 'output-success');
            } else {
                formatDiskInternal();
                printOutput('✓ Disco formatado com sucesso', 'output-success');
            }
        }
        
        function cmdMethod(args) {
            if (args.length === 0) {
                const methodNames = {
                    'encadeada': 'Encadeada (FAT)',
                    'contigua': 'Contígua', 
                    'indexada': 'Indexada (inode)'
                };
                printOutput(`Método atual: ${methodNames[disk.method]}`);
                return;
            }
            
            const newMethod = args[0].toLowerCase();
            if (['contigua', 'encadeada', 'indexada'].includes(newMethod)) {
                if (Object.keys(disk.files).length > 0) {
                    printOutput('Erro: Mude o método apenas quando o disco estiver vazio', 'output-error');
                    return;
                }
                
                disk.method = newMethod;
                printOutput(`✓ Método alterado para: ${newMethod}`, 'output-success');
                updateDisplay();
            } else {
                printOutput('Método inválido. Use: contigua, encadeada ou indexada', 'output-error');
            }
        }
        
        function cmdBlocks(args) {
            if (args.length === 0) {
                printOutput('Uso: blocks <nome_do_arquivo>', 'output-error');
                return;
            }
            
            const file = disk.files[args[0]];
            if (!file) {
                printOutput(`blocks: ${args[0]}: Arquivo não encontrado`, 'output-error');
                return;
            }
            
            printOutput(`Blocos do arquivo '${file.name}':`, 'output-info');
            
            if (disk.method === 'encadeada') {
                let chain = '';
                for (let i = 0; i < file.blocks.length; i++) {
                    const block = file.blocks[i];
                    chain += `${block}`;
                    if (i < file.blocks.length - 1) {
                        chain += ' → ';
                    }
                }
                printOutput(`Cadeia: ${chain}`);
            } else if (disk.method === 'contigua') {
                printOutput(`Sequência contígua: ${file.blocks[0]} - ${file.blocks[file.blocks.length - 1]}`);
            } else if (disk.method === 'indexada') {
                printOutput(`Bloco índice ${file.indexBlock} aponta para: ${file.blocks.join(', ')}`);
            }
            
            printOutput(`Lista completa: [${file.blocks.join(', ')}]`);
        }
        
        function cmdUname() {
            printOutput('Linux FileSim 6.1.0-simulator #1 SMP Simulated File System', 'output-info');
        }
        
        function cmdDate() {
            const now = new Date();
            printOutput(now.toLocaleString('pt-BR', { 
                weekday: 'long', 
                year: 'numeric', 
                month: 'long', 
                day: 'numeric',
                hour: '2-digit',
                minute: '2-digit',
                second: '2-digit'
            }));
        }
        
        function cmdEcho(args) {
            printOutput(args.join(' '));
        }
        
        function cmdPwd() {
            printOutput('/home/root/simulator');
        }
        
        // File System Functions
        function createFileInternal(name, size) {
            if (disk.files[name]) {
                printOutput(`Erro: Arquivo '${name}' já existe`, 'output-error');
                return false;
            }
            
            if (size > 100) {
                printOutput('Erro: Tamanho máximo é 100 blocos', 'output-error');
                return false;
            }
            
            const freeBlocks = disk.blocks.filter(b => !b.occupied);
            if (freeBlocks.length < size) {
                printOutput(`Erro: Espaço insuficiente. Necessário: ${size}, Disponível: ${freeBlocks.length}`, 'output-error');
                return false;
            }
            
            let allocatedBlocks = [];
            
            switch(disk.method) {
                case 'contigua':
                    allocatedBlocks = allocateContiguous(size);
                    break;
                case 'encadeada':
                    allocatedBlocks = allocateLinked(size);
                    break;
                case 'indexada':
                    allocatedBlocks = allocateIndexed(size);
                    break;
            }
            
            if (allocatedBlocks.length !== size) {
                printOutput('Erro: Não foi possível alocar blocos', 'output-error');
                return false;
            }
            
            // Create file
            disk.files[name] = {
                name: name,
                size: size,
                blocks: allocatedBlocks,
                indexBlock: disk.method === 'indexada' ? allocatedBlocks[0] : null
            };
            
            // Mark blocks as occupied
            if (disk.method === 'indexada') {
                // First block is index block
                disk.blocks[allocatedBlocks[0]].occupied = true;
                disk.blocks[allocatedBlocks[0]].fileName = `${name} [ÍNDICE]`;
                
                // Data blocks
                for (let i = 1; i < allocatedBlocks.length; i++) {
                    disk.blocks[allocatedBlocks[i]].occupied = true;
                    disk.blocks[allocatedBlocks[i]].fileName = name;
                }
            } else {
                // All blocks are data blocks
                for (let i = 0; i < allocatedBlocks.length; i++) {
                    disk.blocks[allocatedBlocks[i]].occupied = true;
                    disk.blocks[allocatedBlocks[i]].fileName = name;
                    
                    // Set next block pointer for linked allocation
                    if (disk.method === 'encadeada' && i < allocatedBlocks.length - 1) {
                        disk.blocks[allocatedBlocks[i]].nextBlock = allocatedBlocks[i + 1];
                    } else if (disk.method === 'encadeada') {
                        disk.blocks[allocatedBlocks[i]].nextBlock = -1; // End of chain
                    }
                }
            }
            
            updateDisplay();
            return true;
        }
        
        function allocateContiguous(size) {
            let start = -1;
            let count = 0;
            
            for (let i = 0; i < disk.blocks.length; i++) {
                if (!disk.blocks[i].occupied) {
                    if (count === 0) start = i;
                    count++;
                    if (count === size) {
                        return Array.from({length: size}, (_, j) => start + j);
                    }
                } else {
                    count = 0;
                    start = -1;
                }
            }
            return [];
        }
        
        function allocateLinked(size) {
            const freeBlocks = disk.blocks
                .map((block, index) => ({block, index}))
                .filter(({block}) => !block.occupied)
                .slice(0, size)
                .map(({index}) => index);
            
            return freeBlocks.length === size ? freeBlocks : [];
        }
        
        function allocateIndexed(size) {
            const freeBlocks = disk.blocks
                .map((block, index) => ({block, index}))
                .filter(({block}) => !block.occupied)
                .slice(0, size + 1) // +1 for index block
                .map(({index}) => index);
            
            if (freeBlocks.length < size + 1) return [];
            
            // First block is index block, rest are data blocks
            return [freeBlocks[0], ...freeBlocks.slice(1, size + 1)];
        }
        
        function deleteFileInternal(name) {
            if (!disk.files[name]) {
                return false;
            }
            
            const file = disk.files[name];
            
            // Free all blocks
            file.blocks.forEach(blockId => {
                disk.blocks[blockId].occupied = false;
                disk.blocks[blockId].fileName = null;
                disk.blocks[blockId].nextBlock = null;
            });
            
            // If indexed, also free the index block
            if (file.indexBlock !== null) {
                disk.blocks[file.indexBlock].occupied = false;
                disk.blocks[file.indexBlock].fileName = null;
            }
            
            delete disk.files[name];
            
            if (disk.selectedFile === name) {
                disk.selectedFile = null;
            }
            
            updateDisplay();
            return true;
        }
        
        function formatDiskInternal() {
            disk.blocks = Array(100).fill(null).map((_, i) => ({
                id: i,
                occupied: false,
                fileName: null,
                nextBlock: null
            }));
            disk.files = {};
            disk.selectedFile = null;
            updateDisplay();
        }
        
        function calculateFragmentation(file) {
            if (file.blocks.length <= 1) return 0;
            
            let gaps = 0;
            for (let i = 1; i < file.blocks.length; i++) {
                if (file.blocks[i] !== file.blocks[i-1] + 1) {
                    gaps++;
                }
            }
            
            return Math.round((gaps / (file.blocks.length - 1)) * 100);
        }
        
        // Modal Functions
        function showCreateModal() {
            document.getElementById('createModal').classList.add('show');
            document.getElementById('fileName').focus();
        }
        
        function closeModal() {
            document.getElementById('createModal').classList.remove('show');
        }
        
        function createFile() {
            const name = document.getElementById('fileName').value.trim();
            const size = parseInt(document.getElementById('fileSize').value);
            
            if (!name) {
                alert('Por favor, digite um nome para o arquivo');
                return;
            }
            
            if (isNaN(size) || size < 1 || size > 100) {
                alert('Tamanho deve ser entre 1 e 100 blocos');
                return;
            }
            
            if (createFileInternal(name, size)) {
                printOutput(`✓ Arquivo '${name}' criado com ${size} blocos`, 'output-success');
            } else {
                printOutput(`✗ Erro ao criar arquivo '${name}'`, 'output-error');
            }
            
            closeModal();
            document.getElementById('fileName').value = '';
            document.getElementById('fileSize').value = '5';
        }
        
        function deleteFile() {
            if (!disk.selectedFile) {
                printOutput('Nenhum arquivo selecionado', 'output-error');
                return;
            }
            
            if (deleteFileInternal(disk.selectedFile)) {
                printOutput(`✓ Arquivo '${disk.selectedFile}' removido`, 'output-success');
            } else {
                printOutput(`✗ Erro ao remover arquivo '${disk.selectedFile}'`, 'output-error');
            }
        }
        
        function formatDisk() {
            if (Object.keys(disk.files).length > 0) {
                if (!confirm('Todos os arquivos serão perdidos! Continuar?')) {
                    return;
                }
            }
            
            formatDiskInternal();
            printOutput('✓ Disco formatado com sucesso', 'output-success');
            printWelcome();
        }
        
        // Initialize the disk when page loads
        window.onload = initDisk;
        
        // Close modal when clicking outside
        window.onclick = function(event) {
            const modal = document.getElementById('createModal');
            if (event.target === modal) {
                closeModal();
            }
        }
        
        // Allow Enter key in modal
        document.getElementById('fileName').addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                createFile();
            }
        });
        
        document.getElementById('fileSize').addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                createFile();
            }
        });
    </script>
</body>
</html>