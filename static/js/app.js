document.addEventListener('DOMContentLoaded', function() {
    // 元素引用
    const fileUpload = document.getElementById('fileUpload');
    const uploadedFiles = document.getElementById('uploadedFiles');
    const questionForm = document.getElementById('questionForm');
    const questionInput = document.getElementById('questionInput');
    const chatContainer = document.getElementById('chatContainer');
    const sendBtn = document.getElementById('sendBtn');
    const chatTitle = document.getElementById('chatTitle');
    const newChatBtn = document.getElementById('newChatBtn');
    const historyList = document.getElementById('historyList');
    const toggleSidebarBtn = document.getElementById('toggleSidebarBtn');
    const sidebar = document.querySelector('.sidebar');
    
    // 上传进度模态框
    const uploadProgressModal = document.getElementById('uploadProgressModal');
    const uploadProgressBar = document.getElementById('uploadProgressBar');
    const uploadStatus = document.getElementById('uploadStatus');
    
    // 聊天和状态管理
    let currentChatId = generateChatId();
    let conversations = JSON.parse(localStorage.getItem('conversations')) || {};
    let isProcessing = false;
    let filesUploaded = false;
    
    // 初始化
    initializeApp();
    
    // 应用程序初始化
    function initializeApp() {
        // 创建默认对话（如果不存在）
        if (!conversations[currentChatId]) {
            conversations[currentChatId] = {
                title: '新对话',
                messages: []
            };
            saveToLocalStorage();
        }
        
        // 渲染对话历史记录
        renderChatHistory();
        
        // 检查是否有上传的文件
        checkUploadedFiles();
        
        // 注册事件监听器
        registerEventListeners();
    }
    
    // 检查是否有已上传的文件
    function checkUploadedFiles() {
        fetchFileList();
    }
    
    // 注册事件监听器
    function registerEventListeners() {
        // 文本框自动调整高度
        questionInput.addEventListener('input', function() {
            this.style.height = 'auto';
            this.style.height = (this.scrollHeight > 50) ? 
                Math.min(this.scrollHeight, 150) + 'px' : '50px';
            
            // 启用/禁用发送按钮
            sendBtn.disabled = this.value.trim() === '' || !filesUploaded;
        });
        
        // 文件上传
        fileUpload.addEventListener('change', handleFileUpload);
        
        // 提交问题
        questionForm.addEventListener('submit', function(e) {
            e.preventDefault();
            if (!isProcessing && questionInput.value.trim() !== '') {
                handleQuestion();
            }
        });
        
        // 新对话
        newChatBtn.addEventListener('click', createNewChat);
        
        // 切换侧边栏（移动版）
        toggleSidebarBtn.addEventListener('click', function() {
            sidebar.classList.toggle('show');
        });
        
        // 点击外部关闭侧边栏
        document.addEventListener('click', function(e) {
            if (window.innerWidth <= 768) {
                if (!sidebar.contains(e.target) && !toggleSidebarBtn.contains(e.target)) {
                    sidebar.classList.remove('show');
                }
            }
        });
        
        // 刷新文件列表
        const refreshFilesBtn = document.getElementById('refreshFilesBtn');
        refreshFilesBtn.addEventListener('click', fetchFileList);
        
        // 重建索引
        const rebuildIndexBtn = document.getElementById('rebuildIndexBtn');
        rebuildIndexBtn.addEventListener('click', rebuildIndex);
    }
    
    // 处理文件上传
    async function handleFileUpload(e) {
        const files = e.target.files;
        if (!files.length) return;
        
        showProgressModal();
        resetProgress();
        
        let successCount = 0;
        let failCount = 0;
        let totalFiles = files.length;
        let uploadedFilesList = [];
        
        for (let i = 0; i < files.length; i++) {
            const file = files[i];
            
            // 检查文件格式
            if (!isValidFileType(file.name)) {
                updateProgress(i, totalFiles, successCount, totalFiles);
                uploadStatus.textContent = `跳过非PPT/PDF文件: ${file.name}`;
                continue;
            }
            
            try {
                updateProgress(i, totalFiles);
                uploadStatus.textContent = `上传中: ${file.name} (${i+1}/${totalFiles})`;
                
                const formData = new FormData();
                formData.append('file', file);
                
                const response = await fetch('/upload', {
                    method: 'POST',
                    body: formData
                });
                
                const result = await response.json();
                
                if (response.ok) {
                    successCount++;
                    const fileInfo = { name: file.name, success: true };
                    uploadedFilesList.push(fileInfo);
                    addFileToList(file.name, true);
                } else {
                    failCount++;
                    const fileInfo = { name: file.name, success: false, error: result.detail || '上传失败' };
                    uploadedFilesList.push(fileInfo);
                    addFileToList(file.name, false, result.detail || '上传失败');
                }
                
                updateProgress(i + 1, totalFiles, successCount, totalFiles);
                
            } catch (error) {
                failCount++;
                console.error('上传出错:', error);
                const fileInfo = { name: file.name, success: false, error: '网络错误' };
                uploadedFilesList.push(fileInfo);
                addFileToList(file.name, false, '网络错误');
            }
        }
        
        // 保存上传的文件列表
        localStorage.setItem('uploadedFiles', JSON.stringify(uploadedFilesList));
        
        // 更新状态和UI
        uploadStatus.textContent = `完成! 成功: ${successCount}, 失败: ${failCount}`;
        
        // 延迟关闭模态框
        setTimeout(() => {
            hideProgressModal();
            
            if (successCount > 0) {
                filesUploaded = true;
                enableChat();
                
                // 如果是第一次上传文件，添加系统消息
                if (!hasMessages()) {
                    addSystemMessage('已成功上传PPT/PDF文件，您现在可以开始提问了！');
                }
            }
            
            // 重置文件输入
            fileUpload.value = '';
            
            // 刷新文件列表
            fetchFileList();
        }, 1500);
    }
    
    // 显示进度模态框
    function showProgressModal() {
        uploadProgressModal.classList.add('show');
    }
    
    // 隐藏进度模态框
    function hideProgressModal() {
        uploadProgressModal.classList.remove('show');
    }
    
    // 重置进度条
    function resetProgress() {
        uploadProgressBar.style.width = '0%';
    }
    
    // 更新进度条
    function updateProgress(current, total, success = null, totalSuccess = null) {
        const baseProgress = Math.round((current / total) * 100);
        let progressPercent = baseProgress;
        
        if (success !== null && totalSuccess !== null) {
            const successProgress = Math.round((success / totalSuccess) * 20);
            progressPercent = baseProgress + successProgress;
        }
        
        uploadProgressBar.style.width = `${Math.min(100, progressPercent)}%`;
    }
    
    // 添加文件到列表
    function addFileToList(fileName, success, errorMsg = '') {
        const fileElement = document.createElement('div');
        fileElement.className = 'file-item';
        
        const statusClass = success ? 'success' : 'error';
        const statusIcon = success ? 
            '<i class="bi bi-check-circle-fill"></i>' : 
            '<i class="bi bi-x-circle-fill"></i>';
            
        fileElement.innerHTML = `
            <div class="file-name" title="${fileName}">${getFileIcon(fileName)} ${fileName}</div>
            <div class="file-status ${statusClass}">
                ${statusIcon}
                <span>${success ? '已索引' : errorMsg}</span>
            </div>
        `;
        
        uploadedFiles.appendChild(fileElement);
    }
    
    // 添加带操作按钮的文件列表项
    function addFileToListWithActions(fileName, success, errorMsg = '') {
        const fileElement = document.createElement('div');
        fileElement.className = 'file-item';
        
        const statusClass = success ? 'success' : 'error';
        const statusIcon = success ? 
            '<i class="bi bi-check-circle-fill"></i>' : 
            '<i class="bi bi-x-circle-fill"></i>';
            
        fileElement.innerHTML = `
            <div class="file-name" title="${fileName}">
                <i class="bi bi-file-earmark-pdf"></i>
                ${fileName}
            </div>
            <div class="file-status ${statusClass}">
                ${statusIcon}
                <span>${success ? '已索引' : errorMsg}</span>
            </div>
            <div class="file-actions">
                <button class="file-action-btn preview" title="预览文件">
                    <i class="bi bi-eye"></i>
                </button>
                <button class="file-action-btn delete" title="删除文件">
                    <i class="bi bi-trash"></i>
                </button>
            </div>
        `;
        
        // 添加删除事件处理
        const deleteBtn = fileElement.querySelector('.delete');
        deleteBtn.addEventListener('click', () => deleteFile(fileName));
        
        // 添加预览事件处理
        const previewBtn = fileElement.querySelector('.preview');
        previewBtn.addEventListener('click', () => previewFile(fileName));
        
        uploadedFiles.appendChild(fileElement);
    }
    
    // 删除文件功能
    async function deleteFile(fileName) {
        if (!confirm(`确定要删除文件 "${fileName}" 吗？`)) {
            return;
        }
        
        try {
            const response = await fetch(`/files/${encodeURIComponent(fileName)}`, {
                method: 'DELETE'
            });
            
            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || `删除失败: ${response.status}`);
            }
            
            // 删除成功
            const result = await response.json();
            console.log(result.message);
            
            // 刷新文件列表
            fetchFileList();
            
            // 如果没有文件了，禁用聊天
            const files = await (await fetch('/list-files')).json();
            if (!files || files.length === 0) {
                filesUploaded = false;
                disableChat('请先上传PDF文件');
            }
            
        } catch (error) {
            console.error('删除文件失败:', error);
            alert(`删除文件失败: ${error.message}`);
        }
    }
    
    // 添加重建索引功能
    async function rebuildIndex() {
        if (!confirm('确定要重建索引吗？这可能需要一些时间。')) {
            return;
        }
        
        try {
            // 显示进度模态框
            showProgressModal();
            uploadStatus.textContent = '正在重建索引...';
            uploadProgressBar.style.width = '50%';
            
            const response = await fetch('/rebuild-index', {
                method: 'POST'
            });
            
            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || `重建失败: ${response.status}`);
            }
            
            // 更新进度
            uploadProgressBar.style.width = '100%';
            
            // 获取结果
            const result = await response.json();
            console.log(result.message);
            uploadStatus.textContent = result.message;
            
            // 延迟关闭模态框
            setTimeout(() => {
                hideProgressModal();
                
                // 刷新文件列表
                fetchFileList();
                
                // 添加系统消息
                addSystemMessage(`索引已重建，共处理了${result.processed_files.length}个PDF文件`);
            }, 1500);
            
        } catch (error) {
            console.error('重建索引失败:', error);
            uploadStatus.textContent = `重建索引失败: ${error.message}`;
            
            // 延迟关闭模态框
            setTimeout(hideProgressModal, 1500);
        }
    }
    
    // 处理用户问题
    async function handleQuestion() {
        const question = questionInput.value.trim();
        
        if (!question || isProcessing) return;
        
        // 获取问题类型
        const questionType = document.getElementById("questionType")?.value || "semantic";
        
        isProcessing = true;
        sendBtn.disabled = true;
        
        // 添加用户消息到聊天界面
        addUserMessage(question);
        
        // 清空输入框并重置高度
        questionInput.value = '';
        resetTextareaHeight(); // 这里调用重置函数
        
        // 添加思考指示器
        const thinkingId = addThinkingIndicator();
        
        // 保存用户消息到历史记录
        if (typeof saveMessageToHistory === 'function') {
            saveMessageToHistory('user', question);
        }
        
        try {
            const formData = new FormData();
            formData.append('question', question);
            formData.append('question_type', questionType);
            
            const response = await fetch('/ask', {
                method: 'POST',
                body: formData
            });
            
            const data = await response.json();
            
            // 移除思考指示器
            removeThinkingIndicator(thinkingId);
            
            // 添加机器人回复
            addBotMessage(data.answer || "抱歉，未能获取回答");
            
            // 保存到对话历史
            if (typeof saveMessageToHistory === 'function' && typeof currentChatId !== 'undefined') {
                saveMessageToHistory('bot', data.answer);
                
                // 如果是第一条消息，更新对话标题
                if (conversations[currentChatId].messages.length <= 2) {
                    updateChatTitle(question);
                }
            }
            
        } catch (error) {
            console.error('请求出错:', error);
            
            // 移除思考指示器
            removeThinkingIndicator(thinkingId);
            
            // 添加错误消息
            addBotMessage('抱歉，处理您的问题时出现错误。请稍后再试。');
        }
        
        // 重置处理状态
        isProcessing = false;
        sendBtn.disabled = false;
        
        // 滚动到底部
        scrollToBottom();
    }
    
    // 添加用户消息
    function addUserMessage(content) {
        const message = document.createElement('div');
        message.className = 'message user-message';
        
        message.innerHTML = `
            <div class="message-inner">
                <div class="message-avatar user">
                    <i class="bi bi-person-fill"></i>
                </div>
                <div class="message-content">
                    <p>${escapeHtml(content)}</p>
                </div>
            </div>
        `;
        
        chatContainer.appendChild(message);
        scrollToBottom();
    }
    
    // 添加机器人消息
    function addBotMessage(content) {
        const message = document.createElement('div');
        message.className = 'message bot-message';
        
        // 处理填空题答案格式
        let processedContent = content;
        const fillBlankMatch = content.match(/答案是"([^"]+)"，来自\[(.*?)第(\d+)页\]/i);
        
        if (fillBlankMatch) {
            const answer = fillBlankMatch[1];
            const fileName = fillBlankMatch[2];
            const pageNum = fillBlankMatch[3];
            
            // 特殊格式化填空题答案
            processedContent = content.replace(
                fillBlankMatch[0],
                `<div class="fill-blank-answer">
                    <div class="answer-label">答案</div>
                    <div class="answer-content">${answer}</div>
                    <div class="answer-source">来自 <span class="file-reference">[${fileName} 第${pageNum}页]</span></div>
                </div>`
            );
        } else {
            // 普通引用处理
            processedContent = content.replace(/\[(.*?)第(\d+)页\]/g, 
                '<span class="file-reference">[$1 第$2页]</span>');
        }
        
        // 处理"来源："部分，添加特殊样式
        const sourcesSectionMatch = processedContent.match(/### 来源：([\s\S]*?)(?=$|### )/);
        
        if (sourcesSectionMatch) {
            const beforeSources = processedContent.substring(0, sourcesSectionMatch.index);
            const sourcesContent = sourcesSectionMatch[0];
            const afterSources = processedContent.substring(sourcesSectionMatch.index + sourcesContent.length);
            
            // 创建格式化的来源部分
            const formattedSources = `
                <div class="sources-section">
                    <div class="sources-title">来源信息</div>
                    ${marked.parse(sourcesContent.replace('### 来源：', ''))}
                </div>
            `;
            
            processedContent = beforeSources + formattedSources + afterSources;
        }
        
        message.innerHTML = `
            <div class="message-inner">
                <div class="message-avatar bot">
                    <i class="bi bi-robot"></i>
                </div>
                <div class="message-content">
                    ${marked.parse(processedContent)}
                </div>
            </div>
        `;
        
        chatContainer.appendChild(message);
        
        // 添加语法高亮
        const codeBlocks = message.querySelectorAll('pre code');
        if (window.hljs && codeBlocks.length > 0) {
            codeBlocks.forEach(block => {
                hljs.highlightElement(block);
            });
        }
        
        scrollToBottom();
    }
    
    // 添加系统消息
    function addSystemMessage(content) {
        const welcomeMessage = document.querySelector('.welcome-message');
        if (welcomeMessage) {
            welcomeMessage.remove();
        }
        
        const message = document.createElement('div');
        message.className = 'message system-message';
        
        message.innerHTML = `
            <div class="message-content text-center">
                <p>${content}</p>
            </div>
        `;
        
        chatContainer.appendChild(message);
        scrollToBottom();
    }
    
    // 添加思考中指示器
    function addThinkingIndicator(id) {
        const message = document.createElement('div');
        message.className = 'message bot-message';
        message.id = id;
        
        message.innerHTML = `
            <div class="message-inner">
                <div class="message-avatar bot">
                    <i class="bi bi-robot"></i>
                </div>
                <div class="message-content">
                    <div class="thinking-indicator">
                        <div class="thinking-dot"></div>
                        <div class="thinking-dot"></div>
                        <div class="thinking-dot"></div>
                    </div>
                </div>
            </div>
        `;
        
        chatContainer.appendChild(message);
        scrollToBottom();
    }
    
    // 移除思考中指示器
    function removeThinkingIndicator(id) {
        const element = document.getElementById(id);
        if (element) {
            element.remove();
        }
    }
    
    // HTML转义
    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
    
    // 滚动到底部
    function scrollToBottom() {
        chatContainer.scrollTop = chatContainer.scrollHeight;
    }
    
    // 生成聊天ID
    function generateChatId() {
        return 'chat-' + Date.now();
    }
    
    // 创建新对话
    function createNewChat() {
        // 保存当前对话
        saveToLocalStorage();
        
        // 创建新对话ID
        currentChatId = generateChatId();
        conversations[currentChatId] = {
            title: '新对话',
            messages: []
        };
        
        // 清空聊天容器
        clearChat();
        
        // 添加欢迎消息
        addWelcomeMessage();
        
        // 更新聊天标题
        chatTitle.textContent = '新对话';
        
        // 保存到本地存储并更新UI
        saveToLocalStorage();
        renderChatHistory();
        
        // 在移动设备上关闭侧边栏
        if (window.innerWidth <= 768) {
            sidebar.classList.remove('show');
        }
    }
    
    // 清空聊天
    function clearChat() {
        chatContainer.innerHTML = '';
    }
    
    // 添加欢迎消息
    function addWelcomeMessage() {
        const welcomeDiv = document.createElement('div');
        welcomeDiv.className = 'welcome-message';
        
        welcomeDiv.innerHTML = `
            <div class="welcome-icon">
                <i class="bi bi-robot"></i>
            </div>
            <h2>欢迎使用PPT智能问答系统</h2>
            <p>上传PPT文件后，即可针对PPT内容提问。</p>
        `;
        
        chatContainer.appendChild(welcomeDiv);
    }
    
    // 保存消息到历史记录
    function saveMessageToHistory(role, content) {
        if (!conversations[currentChatId].messages) {
            conversations[currentChatId].messages = [];
        }
        
        conversations[currentChatId].messages.push({
            role: role,
            content: content,
            timestamp: Date.now()
        });
    }
    
    // 更新聊天标题
    function updateChatTitle(question) {
        // 使用问题的前20个字符作为标题
        const title = question.length > 20 ? question.substring(0, 20) + '...' : question;
        conversations[currentChatId].title = title;
        chatTitle.textContent = title;
        
        saveToLocalStorage();
        renderChatHistory();
    }
    
    // 保存到本地存储
    function saveToLocalStorage() {
        localStorage.setItem('conversations', JSON.stringify(conversations));
    }
    
    // 渲染聊天历史记录
    function renderChatHistory() {
        historyList.innerHTML = '';
        
        // 对对话进行排序：最近的在前面
        const sortedChats = Object.entries(conversations).sort((a, b) => {
            const lastMsgA = a[1].messages.length > 0 ? 
                a[1].messages[a[1].messages.length - 1].timestamp : 0;
            const lastMsgB = b[1].messages.length > 0 ? 
                b[1].messages[b[1].messages.length - 1].timestamp : 0;
            return lastMsgB - lastMsgA;
        });
        
        for (const [id, chat] of sortedChats) {
            // 跳过没有消息的聊天
            if (!chat.messages || chat.messages.length === 0) continue;
            
            const item = document.createElement('div');
            item.className = 'history-item';
            if (id === currentChatId) {
                item.classList.add('active');
            }
            
            item.innerHTML = `
                <div class="history-item-icon">
                    <i class="bi bi-chat-left-text"></i>
                </div>
                <div class="history-item-title">${chat.title}</div>
            `;
            
            item.addEventListener('click', () => loadChat(id));
            
            historyList.appendChild(item);
        }
    }
    
    // 加载聊天
    function loadChat(chatId) {
        if (!conversations[chatId]) return;
        
        // 保存当前聊天
        saveToLocalStorage();
        
        // 设置当前聊天ID
        currentChatId = chatId;
        
        // 清空聊天容器
        clearChat();
        
        // 更新标题
        chatTitle.textContent = conversations[chatId].title;
        
        // 加载消息
        if (conversations[chatId].messages && conversations[chatId].messages.length > 0) {
            conversations[chatId].messages.forEach(msg => {
                if (msg.role === 'user') {
                    addUserMessage(msg.content);
                } else if (msg.role === 'bot') {
                    addBotMessage(msg.content);
                } else if (msg.role === 'system') {
                    addSystemMessage(msg.content);
                }
            });
        } else {
            addWelcomeMessage();
        }
        
        // 更新历史记录UI
        renderChatHistory();
        
        // 在移动设备上关闭侧边栏
        if (window.innerWidth <= 768) {
            sidebar.classList.remove('show');
        }
    }
    
    // 检查是否有消息
    function hasMessages() {
        return conversations[currentChatId].messages && 
               conversations[currentChatId].messages.length > 0;
    }
    
    // 启用聊天功能
    function enableChat() {
        questionInput.disabled = false;
        questionInput.placeholder = "输入您的问题...";
        sendBtn.disabled = questionInput.value.trim() === '';
    }
    
    // 禁用聊天功能
    function disableChat(message = '请先上传PPT文件') {
        questionInput.disabled = true;
        questionInput.placeholder = message;
        sendBtn.disabled = true;
    }
    
    // 添加从后端获取文件列表的函数
    async function fetchFileList() {
        try {
            const response = await fetch('/list-files');
            if (!response.ok) {
                throw new Error(`HTTP error: ${response.status}`);
            }
            
            const files = await response.json();
            
            // 清空当前列表
            uploadedFiles.innerHTML = '';
            
            if (files && files.length > 0) {
                filesUploaded = true;
                enableChat();
                
                // 添加文件到UI
                files.forEach(file => {
                    addFileToListWithActions(file.name, true);
                });
                
                // 更新本地存储
                localStorage.setItem('uploadedFiles', JSON.stringify(
                    files.map(file => ({name: file.name, success: true}))
                ));
            } else {
                filesUploaded = false;
                disableChat('请先上传PPT文件');
                uploadedFiles.innerHTML = '<div class="empty-state">没有上传的PPT文件</div>';
            }
        } catch (error) {
            console.error('获取文件列表失败:', error);
            // 回退到本地存储
            const uploadedFilesList = JSON.parse(localStorage.getItem('uploadedFiles')) || [];
            
            if (uploadedFilesList.length > 0) {
                filesUploaded = true;
                enableChat();
                
                uploadedFilesList.forEach(file => {
                    addFileToListWithActions(file.name, file.success, file.error);
                });
            } else {
                disableChat('请先上传PPT文件');
            }
        }
    }
    
    // 检查文件类型函数
    function isValidFileType(filename) {
        return filename.toLowerCase().endsWith('.pdf');
    }
    
    // 获取文件图标
    function getFileIcon(filename) {
        return '<i class="bi bi-file-earmark-pdf-fill"></i>';
    }
    
    // 添加文件预览功能
    async function previewFile(fileName) {
        try {
            const response = await fetch(`/preview/${encodeURIComponent(fileName)}`);
            
            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || `预览失败: ${response.status}`);
            }
            
            const data = await response.json();
            
            // 显示预览对话框
            showPreviewModal(fileName, data.preview, data.total_pages);
            
        } catch (error) {
            console.error('预览文件失败:', error);
            alert(`预览文件失败: ${error.message}`);
        }
    }
    
    // 添加预览模态框
    function showPreviewModal(fileName, previewContent, totalPages) {
        // 创建模态框
        const modal = document.createElement('div');
        modal.className = 'modal preview-modal';
        
        modal.innerHTML = `
            <div class="modal-content">
                <div class="modal-header">
                    <h3>${fileName}</h3>
                    <button class="close-btn">&times;</button>
                </div>
                <div class="modal-body">
                    <div class="preview-info">总页数: ${totalPages}</div>
                    <div class="preview-content">
                        ${previewContent.map(content => `<div class="preview-page">${content}</div>`).join('')}
                    </div>
                </div>
            </div>
        `;
        
        // 添加关闭事件
        const closeBtn = modal.querySelector('.close-btn');
        closeBtn.addEventListener('click', () => {
            document.body.removeChild(modal);
        });
        
        // 添加点击外部区域关闭
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                document.body.removeChild(modal);
            }
        });
        
        document.body.appendChild(modal);
    }
    
    // 定义重置文本区域高度的函数
    function resetTextareaHeight() {
        // 重置输入框高度
        questionInput.style.height = 'auto';
        questionInput.style.height = (questionInput.scrollHeight > 50) ? 
            Math.min(questionInput.scrollHeight, 150) + 'px' : '50px';
    }
    
    // 在初始化时也调整一次
    questionInput.style.height = 'auto';
    questionInput.style.height = (questionInput.scrollHeight > 50) ? 
        Math.min(questionInput.scrollHeight, 150) + 'px' : '50px';
});