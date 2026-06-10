// API Setup
const api = window.pywebview ? window.pywebview.api : null;

// DOM Elements
const urlInput = document.getElementById('urlInput');
const embedThumb = document.getElementById('embedThumb');
const addBtn = document.getElementById('addBtn');
const queueList = document.getElementById('queueList');
const queueCount = document.getElementById('queueCount');
const clearDoneBtn = document.getElementById('clearDoneBtn');
const sessionCounter = document.getElementById('sessionCounter');
const currentTitle = document.getElementById('currentTitle');
const mainProgressBar = document.getElementById('mainProgressBar');
const pauseBtn = document.getElementById('pauseBtn');
const cancelBtn = document.getElementById('cancelBtn');
const logBox = document.getElementById('logBox');

// Modal Elements
const modal = document.getElementById('playlistModal');
const modalSubtitle = document.getElementById('modalSubtitle');
const modalLoading = document.getElementById('modalLoading');
const modalLoadingText = document.getElementById('modalLoadingText');
const modalContent = document.getElementById('modalContent');
const playlistTracks = document.getElementById('playlistTracks');
const modalCancel = document.getElementById('modalCancel');
const modalConfirm = document.getElementById('modalConfirm');
const modalSelectAll = document.getElementById('modalSelectAll');
const modalDeselectAll = document.getElementById('modalDeselectAll');
const modalSelectionCount = document.getElementById('modalSelectionCount');

// Format Picker Elements
const typeAudio = document.getElementById('typeAudio');
const typeVideo = document.getElementById('typeVideo');
const audioQualityWrap = document.getElementById('audioQualityWrap');
const videoQualityWrap = document.getElementById('videoQualityWrap');
const videoQualityInput = document.getElementById('videoQualityInput');
const qualityInput = document.getElementById('qualityInput');
const formatPickerRow = document.getElementById('formatPickerRow');

// State Variables
let queue = [];
let currentPlaylist = [];
let selectedPlaylistIndices = new Set();
let playlistUrl = "";
let currentPlaylistTitle = "Playlist";
let activeDownloadId = null;
let downloadType = 'audio';
let selectedFolder = "";

// Track which playlist groups are open
const openPlaylistGroups = new Set();
