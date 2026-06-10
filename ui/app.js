// Initialize
window.addEventListener('pywebviewready', () => {
    console.log("PyWebView Ready");
    window.pywebview.api.js_ready();
});

if (typeAudio && typeVideo) {
    typeAudio.onclick = () => {
        downloadType = 'audio';
        typeAudio.classList.add('active');
        typeVideo.classList.remove('active');
        audioQualityWrap.classList.remove('hidden');
        videoQualityWrap.classList.add('hidden');
    };

    typeVideo.onclick = () => {
        downloadType = 'video';
        typeVideo.classList.add('active');
        typeAudio.classList.remove('active');
        videoQualityWrap.classList.remove('hidden');
        audioQualityWrap.classList.add('hidden');
        
        if (videoQualityInput.options.length <= 1 && (!currentPlaylist || currentPlaylist.length !== 1 || !currentPlaylist[0].available_heights)) {
            videoQualityInput.innerHTML = `
                <option value="bestvideo+bestaudio/best">Best available</option>
                <option value="bestvideo[height<=2160]+bestaudio/best[height<=2160]">4K 2160p</option>
                <option value="bestvideo[height<=1440]+bestaudio/best[height<=1440]">1440p</option>
                <option value="bestvideo[height<=1080]+bestaudio/best[height<=1080]">1080p</option>
                <option value="bestvideo[height<=720]+bestaudio/best[height<=720]">720p</option>
                <option value="bestvideo[height<=480]+bestaudio/best[height<=480]">480p</option>
                <option value="bestvideo[height<=360]+bestaudio/best[height<=360]">360p</option>
            `;
        }
    };
}

// Exposed functions for Python to call
window.syncQueue = (items) => {
    queue = items;
    renderQueue();
    updateControls();
};

window.updateProgress = (id, pct) => {
    // Update active row progress bar (if rendered)
    const el = document.getElementById(`prog-${id}`);
    if (el) el.style.width = `${pct}%`;

    // Update main sidebar — only for the active download
    if (id === activeDownloadId) {
        mainProgressBar.style.width = `${pct}%`;
    }
};

window.addLog = (msg, tag = 'info') => {
    const div = document.createElement('div');
    div.innerHTML = msg;
    if (tag) div.className = `log-${tag}`;
    logBox.appendChild(div);
    if (logBox.childElementCount > 300) {
        logBox.removeChild(logBox.firstChild);
    }
    logBox.scrollTop = logBox.scrollHeight;
};

// Playlist Callback
window.onPlaylistProgress = (count) => {
    modalLoadingText.innerText = `Fetching playlist... ${count} tracks found`;
};

window.onPlaylistLoaded = (entries) => {
    currentPlaylist = entries;
    selectedPlaylistIndices = new Set(entries.map((_, i) => i));

    // Dynamic resolution population for single videos
    if (entries.length === 1 && entries[0].available_heights) {
        const heights = entries[0].available_heights;
        let html = `<option value="bestvideo+bestaudio/best">Best available</option>`;
        heights.forEach(h => {
            html += `<option value="bestvideo[height<=${h}]+bestaudio/best[height<=${h}]">${h}p</option>`;
        });
        videoQualityInput.innerHTML = html;
        
        // Populate audio abrs if available
        if (entries[0].available_abrs && entries[0].available_abrs.length > 0) {
            let aHtml = '';
            entries[0].available_abrs.forEach(abr => {
                aHtml += `<option value="${abr}">${abr} kbps</option>`;
            });
            qualityInput.innerHTML = aHtml;
        }
    } else {
        // Reset to default generic options for playlists
        videoQualityInput.innerHTML = `
            <option value="bestvideo+bestaudio/best">Best available</option>
            <option value="bestvideo[height<=2160]+bestaudio/best[height<=2160]">4K 2160p</option>
            <option value="bestvideo[height<=1440]+bestaudio/best[height<=1440]">1440p</option>
            <option value="bestvideo[height<=1080]+bestaudio/best[height<=1080]">1080p</option>
            <option value="bestvideo[height<=720]+bestaudio/best[height<=720]">720p</option>
            <option value="bestvideo[height<=480]+bestaudio/best[height<=480]">480p</option>
            <option value="bestvideo[height<=360]+bestaudio/best[height<=360]">360p</option>
        `;
        qualityInput.innerHTML = `
            <option value="96">96 kbps — Low</option>
            <option value="128">128 kbps — Standard</option>
            <option value="192" selected>192 kbps — High</option>
            <option value="256">256 kbps — Very High</option>
            <option value="320">320 kbps — Maximum</option>
        `;
    }

    if (entries.length === 0) {
        currentPlaylistTitle = "Playlist";
        modalSubtitle.innerText = `No tracks found`;
        playlistTracks.innerHTML = `
            <div class="empty-state" style="padding: 24px 10px; border-style: dashed;">
                <i class="ph ph-warning-circle" style="font-size: 28px; color: var(--warning); margin-bottom: 8px;"></i>
                <p style="font-size: 0.9rem; font-weight: 500;">No tracks or videos could be fetched.</p>
                <span style="font-size: 0.75rem; color: var(--text-muted);">Please check the link and try again.</span>
            </div>
        `;
        modalLoading.classList.add('hidden');
        modalContent.classList.remove('hidden');
        modalConfirm.disabled = true;
        if (formatPickerRow) formatPickerRow.classList.add('hidden');
        return;
    }

    const isPlaylist = entries.length > 1 || (entries.length === 1 && (entries[0].playlist_title || entries[0].playlist_id));
    
    if (!isPlaylist && entries.length === 1) {
        currentPlaylistTitle = entries[0].title || "Single Video";
        modalSubtitle.innerText = `Single Video`;
    } else {
        currentPlaylistTitle = (entries.length > 0 && entries[0].playlist_title) ? entries[0].playlist_title : "Playlist";
        modalSubtitle.innerText = `${currentPlaylistTitle} — ${entries.length} tracks`;
    }
    
    modalLoading.classList.add('hidden');
    modalContent.classList.remove('hidden');
    modalConfirm.disabled = false;
    if (formatPickerRow) formatPickerRow.classList.remove('hidden');
    
    renderPlaylistModal();
};

window.playlistAction = (id, action) => {
    if (window.pywebview) window.pywebview.api.playlist_action(id, action);
};

window.removeItem = (id) => {
    if (window.pywebview) window.pywebview.api.remove_item(id);
};

// Event Bindings
addBtn.onclick = async () => {
    const url = urlInput.value.trim();
    if (!url) {
        alert("Please enter a URL.");
        return;
    }

    const folder = await window.pywebview.api.ask_folder();
    if (!folder) return; // Cancelled

    playlistUrl = url;
    selectedFolder = folder;
    
    // Open Modal
    modal.classList.add('active');
    modalLoading.classList.remove('hidden');
    modalContent.classList.add('hidden');
    if (formatPickerRow) formatPickerRow.classList.add('hidden');
    modalConfirm.disabled = true;
    modalSubtitle.innerText = 'Loading...';
    
    // Fetch
    window.pywebview.api.fetch_playlist(url);
};

clearDoneBtn.onclick = () => {
    if (window.pywebview) window.pywebview.api.clear_done();
};

pauseBtn.onclick = () => {
    if (window.pywebview) window.pywebview.api.pause_resume();
};

cancelBtn.onclick = () => {
    if (window.pywebview) window.pywebview.api.cancel_current();
};

modalCancel.onclick = () => {
    modal.classList.remove('active');
};

const modalCloseX = document.getElementById('modalCloseX');
if (modalCloseX) {
    modalCloseX.onclick = () => {
        modal.classList.remove('active');
    };
}

modalSelectAll.onclick = () => {
    selectedPlaylistIndices = new Set(currentPlaylist.map((_, i) => i));
    renderPlaylistModal();
};

modalDeselectAll.onclick = () => {
    selectedPlaylistIndices.clear();
    renderPlaylistModal();
};

modalConfirm.onclick = () => {
    const selectedEntries = currentPlaylist.filter((_, i) => selectedPlaylistIndices.has(i));
    if (selectedFolder && selectedEntries.length > 0) {
        const folder = selectedFolder;
        const type = downloadType;
        const quality = type === 'audio' ? qualityInput.value : videoQualityInput.value;
        const embed = embedThumb.checked;
        const title = currentPlaylistTitle;

        // Reset inputs and close modal immediately
        modal.classList.remove('active');
        urlInput.value = "";
        selectedFolder = "";

        // Call backend API in background
        window.pywebview.api.add_playlist_items(selectedEntries, folder, quality, embed, title, type);
    }
};
