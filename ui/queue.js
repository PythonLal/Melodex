// UI Rendering
function renderQueue() {
    queueCount.innerText = queue.length;
    if (queue.length === 0) {
        queueList.innerHTML = `
            <div class="empty-state">
                <i class="ph ph-music-notes"></i>
                <p>No items in queue yet.</p>
                <span>Add a URL above to get started.</span>
            </div>
        `;
        return;
    }

    queueList.innerHTML = '';
    
    // Group by playlist_id
    const groups = [];
    const grouped = new Map();
    queue.forEach(item => {
        if (!item.playlist_id) {
            groups.push(item); // Single item
        } else {
            if (!grouped.has(item.playlist_id)) {
                const arr = [];
                grouped.set(item.playlist_id, arr);
                groups.push({ isPlaylist: true, id: item.playlist_id, title: item.playlist_title || "Playlist", items: arr });
            }
            grouped.get(item.playlist_id).push(item);
        }
    });

    const createItemHtml = (item) => {
        const isDone = item.status === 'done';
        const isErr = item.status === 'error';
        
        let statusHtml = '';
        if (isDone) statusHtml = `<span class="status-badge done">✅ Done</span>`;
        else if (isErr) statusHtml = `<span class="status-badge error">❌ Error</span>`;
        else if (item.status === 'downloading') statusHtml = `<span class="accent-text">⬇ ${Math.round(item.progress)}%</span>`;
        else if (item.status === 'paused') statusHtml = `<span style="color:var(--text-muted)">⏸ Paused</span>`;
        else statusHtml = `<span style="color:var(--text-muted)">⏳ Waiting</span>`;

        let progBar = '';
        if (item.status === 'downloading' || item.status === 'paused') {
            progBar = `<div class="progress-bg" style="margin-top:8px"><div id="prog-${item.id}" class="progress-fill" style="width: ${item.progress}%"></div></div>`;
        }

        const title = item.title || item.url;
        const shortFolder = item.folder.length > 30 ? '...' + item.folder.slice(-27) : item.folder;

        return `
            <div class="q-item ${item.status === 'downloading' || item.status === 'paused' ? 'active' : ''}">
                <div class="status-dot ${item.status}"></div>
                <div class="q-details">
                    <div class="q-title truncate">${title}</div>
                    <div class="q-meta">${shortFolder} · ${item.quality} kbps</div>
                    ${progBar}
                </div>
                <div class="q-actions">
                    ${statusHtml}
                    ${(item.status !== 'downloading' && item.status !== 'paused') ? `<button class="btn btn-icon danger" onclick="window.removeItem('${item.id}')" title="Remove"><i class="ph ph-trash"></i></button>` : ''}
                </div>
            </div>
        `;
    };

    groups.forEach(group => {
        if (!group.isPlaylist) {
            const temp = document.createElement('div');
            temp.innerHTML = createItemHtml(group);
            queueList.appendChild(temp.firstElementChild);
        } else {
            const details = document.createElement('details');
            details.className = 'playlist-group';
            details.dataset.playlistId = group.id;

            if (openPlaylistGroups.has(group.id)) details.open = true;

            details.addEventListener('toggle', () => {
                if (details.open) openPlaylistGroups.add(group.id);
                else openPlaylistGroups.delete(group.id);
            });

            const total = group.items.length;
            const doneCount = group.items.filter(i => i.status === 'done').length;
            const errCount = group.items.filter(i => i.status === 'error').length;
            const downCount = group.items.filter(i => i.status === 'downloading').length;
            const pausedCount = group.items.filter(i => i.status === 'paused').length;
            
            const aggProgress = group.items.reduce((sum, i) => {
                if (i.status === 'done') return sum + 100;
                if (i.status === 'downloading' || i.status === 'paused') return sum + (i.progress || 0);
                return sum;
            }, 0) / total;
            
            let statusText = `${doneCount}/${total} done`;
            if (errCount > 0) statusText += ` · ${errCount} failed`;
            if (downCount > 0) statusText = `Downloading... ${doneCount}/${total}`;
            if (pausedCount > 0 && downCount === 0) statusText = `Paused · ${doneCount}/${total} done`;

            const progBarHtml = (downCount > 0 || doneCount > 0) 
                ? `<div class="progress-bg" style="margin-top:8px"><div class="progress-fill" style="width: ${aggProgress}%"></div></div>` 
                : '';

            details.innerHTML = `
                <summary class="playlist-summary q-item">
                    <div class="status-dot ${downCount > 0 ? 'downloading' : (doneCount === total ? 'done' : (pausedCount > 0 ? 'paused' : 'waiting'))}"></div>
                    <div class="q-details">
                        <div class="q-title truncate">📁 ${group.title}</div>
                        <div class="q-meta">${statusText}</div>
                        ${progBarHtml}
                    </div>
                    <div class="q-actions" onclick="event.preventDefault(); event.stopPropagation();">
                        <button class="btn btn-icon" onclick="window.playlistAction('${group.id}', 'resume')" title="Continue All"><i class="ph ph-play"></i></button>
                        <button class="btn btn-icon" onclick="window.playlistAction('${group.id}', 'pause')" title="Pause All"><i class="ph ph-pause"></i></button>
                        <button class="btn btn-icon danger" onclick="window.playlistAction('${group.id}', 'cancel')" title="Cancel All"><i class="ph ph-trash"></i></button>
                    </div>
                </summary>
                <div class="playlist-items">
                    ${group.items.map(createItemHtml).join('')}
                </div>
            `;
            queueList.appendChild(details);
        }
    });

    // Auto-scroll to the active item in view
    requestAnimationFrame(() => {
        const activeEl = queueList.querySelector('.q-item.active');
        if (activeEl) {
            const parentDetails = activeEl.closest('details.playlist-group');
            const target = (parentDetails && !parentDetails.open) ? parentDetails : activeEl;
            target.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        }
    });
}

function updateControls() {
    const activeItem = queue.find(i => i.status === 'downloading' || i.status === 'paused');
    if (activeItem) {
        activeDownloadId = activeItem.id;
        currentTitle.innerText = activeItem.title || activeItem.url;
        mainProgressBar.style.width = `${activeItem.progress}%`;
        pauseBtn.disabled = false;
        cancelBtn.disabled = false;
        pauseBtn.innerHTML = activeItem.status === 'paused'
            ? '<i class="ph ph-play"></i> Resume'
            : '<i class="ph ph-pause"></i> Pause';
        const waitingCount = queue.filter(i => i.status === 'waiting').length;
        sessionCounter.innerText = `Active (Queue: ${waitingCount})`;
    } else {
        activeDownloadId = null;
        currentTitle.innerText = "Waiting...";
        mainProgressBar.style.width = "0%";
        pauseBtn.disabled = true;
        cancelBtn.disabled = true;
        pauseBtn.innerHTML = '<i class="ph ph-pause"></i> Pause';
        sessionCounter.innerText = "";
    }
}
