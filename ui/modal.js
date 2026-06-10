// Playlist Modal Rendering
function renderPlaylistModal() {
    playlistTracks.innerHTML = '';
    modalSelectionCount.innerText = `${selectedPlaylistIndices.size} selected`;
    modalConfirm.disabled = selectedPlaylistIndices.size === 0;

    const modalToolbar = document.querySelector('.modal-toolbar');
    const isPlaylist = currentPlaylist.length > 1 || (currentPlaylist.length === 1 && (currentPlaylist[0].playlist_title || currentPlaylist[0].playlist_id));
    if (!isPlaylist) {
        if (modalToolbar) modalToolbar.classList.add('hidden');
    } else {
        if (modalToolbar) modalToolbar.classList.remove('hidden');
    }

    currentPlaylist.forEach((track, i) => {
        const isSelected = selectedPlaylistIndices.has(i);
        const div = document.createElement('div');
        div.className = `p-track ${isSelected ? 'selected' : ''}`;
        div.dataset.idx = i;

        const title = track.title || track.id || `Track ${i+1}`;
        const dur = track.duration
            ? `${Math.floor(track.duration / 60)}:${(track.duration % 60).toString().padStart(2, '0')}`
            : '';

        div.innerHTML = `
            <div class="checkbox-container" style="pointer-events: none">
                <input type="checkbox" ${isSelected ? 'checked' : ''}>
                <span class="checkmark"></span>
            </div>
            <span style="color:var(--text-muted); width:30px; font-family:monospace">${i+1}.</span>
            <span class="truncate" style="flex:1">${title}</span>
            <span style="color:var(--text-muted); font-size:0.85rem">${dur}</span>
        `;

        // Toggle only the clicked row — no full re-render
        div.onclick = () => {
            const idx = parseInt(div.dataset.idx, 10);
            const nowSelected = selectedPlaylistIndices.has(idx);
            if (nowSelected) {
                selectedPlaylistIndices.delete(idx);
                div.classList.remove('selected');
                div.querySelector('input[type=checkbox]').checked = false;
            } else {
                selectedPlaylistIndices.add(idx);
                div.classList.add('selected');
                div.querySelector('input[type=checkbox]').checked = true;
            }
            // Update the count and confirm button without rebuilding the list
            modalSelectionCount.innerText = `${selectedPlaylistIndices.size} selected`;
            modalConfirm.disabled = selectedPlaylistIndices.size === 0;
        };

        playlistTracks.appendChild(div);
    });
}
