
import React, { useState, useRef, useEffect, useCallback, useMemo } from 'react';
import { GameState, Tag, Player, Categorizer, Descriptor, Playlist, FilterState, ColorMode, TimelineGrouping, DrawPath } from './types';
import Timeline from './components/Timeline';
import Telestrator from './components/Telestrator';
import KeyboardOverlay from './components/KeyboardOverlay';
import CourtMap from './components/CourtMap';
import Modal from './components/Modal';
import SettingsModal from './components/SettingsModal';
import ResizableSplit from './components/ResizableSplit';
import { ToastContainer, ToastMessage } from './components/Toast';
import SplashScreen from './components/SplashScreen';
import PresenterMode from './components/PresenterMode';
import PresenterView from './components/PresenterView';
import EmptyStateIllustration from './components/EmptyStateIllustration';
import { formatTime, formatGameClock, parseGameClock, generateCSVBlob, generateBoxScoreCSV, generatePlayByPlayCSV, generatePremiereXML, generatePlaylistsCSV, downloadFile, generateId, getSampleGame, getGameClockSeconds, drawFrameOnCanvas, generateAnalyticsCSV, getPeriodLength, getPeriodLabel } from './utils/helpers';
import {
    Play, Pause, Upload, Check, CheckCircle,
    SkipBack, SkipForward, ChevronLeft, ChevronRight, Clock,
    Volume2, VolumeX, Maximize, CornerUpRight, Gauge, PictureInPicture,
    Film, Download, StopCircle, FileSpreadsheet, Loader2, PenTool, X
} from 'lucide-react';
import { GameProvider, useGame, initialGame } from './context/GameContext';
import { useVideoPlayer } from './hooks/useVideoPlayer';
import { useAppShortcuts } from './hooks/useAppShortcuts';
import Sidebar from './components/Sidebar';
import Header from './components/Header';
import VideoPreviewTooltip from './components/VideoPreviewTooltip';
import { TimeInput, GameClockInput } from './components/inputs/TimeInputs';

// Lazy Load Views
const AnalyticsView = React.lazy(() => import('./components/AnalyticsView'));
const PlaylistView = React.lazy(() => import('./components/PlaylistView'));
const DataMatrix = React.lazy(() => import('./components/DataMatrix'));
const ComparisonView = React.lazy(() => import('./components/ComparisonView'));

// Types and Initial States
type WorkflowStep =
    | 'shooter' | 'assist' | 'rebound' | 'rebound_team' | 'rebound_player' | 'blocker' | 'turnover_player'
    | 'turnover_type' | 'turnover_forcer' | 'stealer' | 'victim'
    | 'foul_committer' | 'foul_type' | 'ft_shooter' | 'sub_out' | 'sub_in'
    | 'jump_ball_contesters' | 'jump_ball_winner' | 'timeout_team' | 'idle';

interface WorkflowState {
    active: boolean;
    step: WorkflowStep;
    primaryAction: Categorizer | null;
    data: {
        shooter?: Player;
        assist?: Player | 'none';
        rebounder?: Player | 'team_off' | 'team_def' | 'team';
        reboundTeamSide?: 'home' | 'away';
        blocker?: Player;
        turnoverPlayer?: Player;
        turnoverType?: string;
        turnoverForcer?: Player | 'none';
        stealer?: Player;
        victim?: Player;
        foulCommitter?: Player;
        foulType?: string;
        subOut?: Player;
        subIn?: Player;
        contesters?: Player[];
        jumpWinner?: Player;
        timeoutTeam?: 'home' | 'away';
        timestamp: number;
        gameClock: number;
    };
}

const initialWorkflowState: WorkflowState = {
    active: false,
    step: 'idle',
    primaryAction: null,
    data: { timestamp: 0, gameClock: 0 }
};

const LAYOUT_STORAGE_KEY = 'tappa_layout_settings';

const AppContent: React.FC = () => {
    const { game, dispatch, canUndo, canRedo, isLoading } = useGame();

    const savedLayout = useMemo(() => {
        const data = localStorage.getItem(LAYOUT_STORAGE_KEY);
        if (data) {
            try { return JSON.parse(data); } catch (e) { return {}; }
        }
        return {};
    }, []);

    const [workflow, setWorkflow] = useState<WorkflowState>(initialWorkflowState);
    const [ambiguousMatches, setAmbiguousMatches] = useState<Player[] | null>(null);
    const [showSplash, setShowSplash] = useState(true);

    const broadcastChannel = useMemo(() => new BroadcastChannel('tappa_channel'), []);

    const [playlists, setPlaylists] = useState<Playlist[]>([]);
    const [enabledViews, setEnabledViews] = useState<string[]>(
        savedLayout.enabledViews || ['tagger', 'analytics', 'playlists']
    );

    const initialView = savedLayout.defaultView && enabledViews.includes(savedLayout.defaultView) ? savedLayout.defaultView : 'tagger';
    const [view, setView] = useState<'tagger' | 'analytics' | 'playlists' | 'matrix' | 'annotator' | 'presenter' | 'comparison'>(initialView);
    const [defaultView, setDefaultView] = useState<string>(initialView);

    const [sidebarTab, setSidebarTab] = useState<'console' | 'editor'>('console');
    const [isSettingsOpen, setIsSettingsOpen] = useState(false);
    const [isExportModalOpen, setIsExportModalOpen] = useState(false);
    const [isShortcutsOpen, setIsShortcutsOpen] = useState(false);
    const [isStartersModalOpen, setIsStartersModalOpen] = useState(false);
    const [isLocationModalOpen, setIsLocationModalOpen] = useState(false);
    const [toasts, setToasts] = useState<ToastMessage[]>([]);
    const [installPrompt, setInstallPrompt] = useState<any>(null);

    const [exportConfig, setExportConfig] = useState<{
        type: 'raw' | 'box' | 'pbp' | 'xml' | 'playlists' | 'analytics';
        scope: 'game' | 'half' | 'quarter';
    }>({ type: 'box', scope: 'game' });
    const [exportFileName, setExportFileName] = useState('');

    const {
        videoRef, videoSrc, setVideoSrc, isPlaying, setIsPlaying,
        currentTime, setCurrentTime, duration, setDuration,
        playbackRate, setPlaybackRate, isMuted, setIsMuted,
        togglePlay, handleSeek, handleTimeUpdate, handleLoadedMetadata,
        toggleMute, fps, setFps, currentFrame, stepFrame
    } = useVideoPlayer();

    const [isSpeedMenuOpen, setIsSpeedMenuOpen] = useState(false);
    const [isFpsMenuOpen, setIsFpsMenuOpen] = useState(false);
    const annotatorVideoRef = useRef<HTMLVideoElement>(null);
    const playerContainerRef = useRef<HTMLDivElement>(null);
    const scrubberRef = useRef<HTMLDivElement>(null);

    const [zoom, setZoom] = useState(savedLayout.zoom || 1);
    const [grouping, setGrouping] = useState<TimelineGrouping>(savedLayout.grouping || 'event');
    const [colorMode, setColorMode] = useState<ColorMode>(savedLayout.colorMode || 'category');
    const [selectedTagIds, setSelectedTagIds] = useState<number[]>([]);
    const [filterState, setFilterState] = useState<FilterState>({});
    const [scrollRequest, setScrollRequest] = useState<number | null>(null);

    const [isRendering, setIsRendering] = useState(false);
    const [renderProgress, setRenderProgress] = useState(0);
    const renderingRef = useRef(false);

    const [hSplit, setHSplit] = useState(savedLayout.hSplit || 60);
    const [vSplit, setVSplit] = useState(savedLayout.vSplit || 70);

    const [isTimelineCollapsed, setIsTimelineCollapsed] = useState(false);
    const lastVSplit = useRef(savedLayout.vSplit || 70);

    const handleToggleTimelineCollapse = useCallback(() => {
        if (isTimelineCollapsed) {
            setVSplit(lastVSplit.current);
            setIsTimelineCollapsed(false);
        } else {
            lastVSplit.current = vSplit;
            setVSplit(90);
            setIsTimelineCollapsed(true);
        }
    }, [isTimelineCollapsed, vSplit]);

    const [scrubHover, setScrubHover] = useState<{ x: number, time: number } | null>(null);

    useEffect(() => {
        const handleBeforeInstallPrompt = (e: any) => {
            e.preventDefault();
            setInstallPrompt(e);
        };
        window.addEventListener('beforeinstallprompt', handleBeforeInstallPrompt);
        return () => window.removeEventListener('beforeinstallprompt', handleBeforeInstallPrompt);
    }, []);

    const handleInstallClick = async () => {
        if (!installPrompt) return;
        installPrompt.prompt();
        const { outcome } = await installPrompt.userChoice;
        if (outcome === 'accepted') setInstallPrompt(null);
    };

    const [activePeriod, setActivePeriod] = useState(savedLayout.activePeriod || 1);

    useEffect(() => {
        const settings = {
            zoom, grouping, colorMode, isMuted, hSplit, vSplit,
            defaultView, enabledViews, activePeriod
        };
        localStorage.setItem(LAYOUT_STORAGE_KEY, JSON.stringify(settings));
    }, [zoom, grouping, colorMode, isMuted, hSplit, vSplit, defaultView, enabledViews, activePeriod]);

    const [isClockSyncOpen, setIsClockSyncOpen] = useState(false);
    const [tempGameClock, setTempGameClock] = useState("12:00");
    const [isGameClockRunning, setIsGameClockRunning] = useState(true);
    const [clockStopTime, setClockStopTime] = useState<number | null>(null);
    const [isJumpOpen, setIsJumpOpen] = useState(false);
    const [jumpTargetTime, setJumpTargetTime] = useState("12:00");

    const [telestratorPaths, setTelestratorPaths] = useState<DrawPath[]>([]);
    const [telestratorRedoStack, setTelestratorRedoStack] = useState<DrawPath[]>([]);
    const [activePlaylistId, setActivePlaylistId] = useState<string | null>(null);

    const currentScore = useMemo(() => {
        let h = 0, a = 0;
        game.tags.forEach(tag => {
            if (tag.startTime <= currentTime && (tag.outcome === 'make' || tag.label.includes('FT Make'))) {
                let pts = 0;
                if (tag.label.includes('3pt')) pts = 3;
                else if (tag.label.includes('FT')) pts = 1;
                else pts = 2;
                if (tag.player?.team === 'home') h += pts;
                else if (tag.player?.team === 'away') a += pts;
            }
        });
        return { home: h, away: a };
    }, [game.tags, currentTime]);

    const projectInputRef = useRef<HTMLInputElement>(null);
    const exportInputRef = useRef<HTMLInputElement>(null);

    const gameRef = useRef(game);
    const selectedTagsRef = useRef(selectedTagIds);
    const videoStateRef = useRef({ currentTime, duration, isPlaying, view, videoSrc });
    const filterStateRef = useRef(filterState);
    const activePeriodRef = useRef(activePeriod);
    const gameClockRef = useRef({ isRunning: isGameClockRunning, stopTime: clockStopTime });
    const workflowRef = useRef(workflow);

    useEffect(() => { gameRef.current = game; }, [game]);
    useEffect(() => { selectedTagsRef.current = selectedTagIds; }, [selectedTagIds]);
    useEffect(() => { videoStateRef.current = { currentTime, duration, isPlaying, view, videoSrc }; }, [currentTime, duration, isPlaying, view, videoSrc]);
    useEffect(() => { filterStateRef.current = filterState; }, [filterState]);
    useEffect(() => { activePeriodRef.current = activePeriod; }, [activePeriod]);
    useEffect(() => { gameClockRef.current = { isRunning: isGameClockRunning, stopTime: clockStopTime }; }, [isGameClockRunning, clockStopTime]);
    useEffect(() => { workflowRef.current = workflow; }, [workflow]);

    useEffect(() => {
        if (isExportModalOpen && exportInputRef.current) setTimeout(() => exportInputRef.current?.focus(), 100);
    }, [isExportModalOpen]);

    useEffect(() => {
        broadcastChannel.onmessage = (event) => {
            if (event.data.type === 'REQUEST_SYNC') {
                broadcastChannel.postMessage({ type: 'SYNC_STATE', payload: { src: videoSrc, time: currentTime, isPlaying: isPlaying, rate: playbackRate } });
            }
        };
    }, [videoSrc, currentTime, isPlaying, playbackRate, broadcastChannel]);

    useEffect(() => { broadcastChannel.postMessage({ type: 'RATE', payload: playbackRate }); }, [playbackRate]);

    const showToast = (message: string, type: 'success' | 'error' | 'info' = 'info') => {
        const id = Date.now().toString();
        setToasts(prev => [...prev, { id, message, type }]);
        setTimeout(() => setToasts(prev => prev.filter(t => t.id !== id)), 3000);
    };

    const handleOpenPresenter = () => window.open('?mode=presenter', '_blank', 'menubar=no,toolbar=no,location=no,status=no,width=1280,height=720');

    const resolveAmbiguity = useCallback((player: Player | null) => {
        if (player) {
            if (workflowRef.current.active) handleWorkflowInput(player);
            else handleAssignPlayer(player);
        } else { showToast("Ambiguous selection cancelled", "info"); }
        setAmbiguousMatches(null);
    }, []);

    const startWorkflow = useCallback((categorizer: Categorizer, initialDescriptors: string[] = []) => {
        if (gameRef.current.activeLineup.length === 0) { setIsStartersModalOpen(true); showToast("Please select starting lineup before tagging", "info"); return; }
        if (Object.keys(filterStateRef.current).length > 0) { showToast("Clear active filter to add new tags", "error"); return; }

        let step: WorkflowStep = 'shooter';
        const label = categorizer.label.toLowerCase();
        const category = categorizer.category;

        if (label.includes('assist')) { showToast("Tag Assist through 'Make' workflow", "info"); return; }

        if (label.includes('rebound') || initialDescriptors.includes('Offensive') || initialDescriptors.includes('Defensive')) { step = 'rebound'; }
        else if (label.includes('turnover')) { step = 'turnover_player'; }
        else if (label.includes('steal')) { step = 'stealer'; }
        else if (label.includes('block')) { step = 'shooter'; }
        else if (label.includes('foul')) { step = 'foul_committer'; }
        else if (label.includes('ft')) { step = 'ft_shooter'; }
        else if (label.includes('sub')) { step = 'sub_out'; }
        else if (label.includes('jump ball')) { step = 'jump_ball_contesters'; }
        else if (label.includes('timeout')) { step = 'timeout_team'; }

        const stopCategories = ['Fouls', 'Turnover', 'Timeout', 'Out of Bounds', 'Stoppage', 'Violation'];
        const shouldStop = stopCategories.some(c => category === c) || label.includes('foul') || label.includes('turnover') || label.includes('sub') || label.includes('timeout');

        if (shouldStop) {
            if (gameClockRef.current.isRunning) {
                setIsGameClockRunning(false);
                setClockStopTime(videoStateRef.current.currentTime);
            }
        }

        const effectiveTime = (!gameClockRef.current.isRunning && gameClockRef.current.stopTime !== null) ? gameClockRef.current.stopTime! : videoStateRef.current.currentTime;
        const gClock = getGameClockSeconds(effectiveTime, activePeriodRef.current, gameRef.current);

        setWorkflow({
            active: true,
            step,
            primaryAction: categorizer,
            data: { timestamp: effectiveTime, gameClock: gClock }
        });
        setSidebarTab('console');
    }, []);

    const handleWorkflowInput = useCallback((input: any) => {
        if (!workflowRef.current.active || !workflowRef.current.primaryAction) return;
        const { step, data, primaryAction } = workflowRef.current;
        const newData = { ...data };
        let nextStep: WorkflowStep | 'finish' = 'finish';

        if (primaryAction.label.includes('Make') && !primaryAction.label.includes('FT')) {
            if (step === 'shooter') { newData.shooter = input; nextStep = 'assist'; } else if (step === 'assist') { newData.assist = input; nextStep = 'finish'; }
        } else if (primaryAction.label.includes('Miss')) {
            if (step === 'shooter') { newData.shooter = input; nextStep = 'rebound_team'; }
            else if (step === 'rebound_team') { if (input === 'none') nextStep = 'finish'; else { newData.rebounder = input; if (input === 'home' || input === 'away') newData.reboundTeamSide = input; nextStep = 'finish'; } }
        } else if (primaryAction.label.includes('Block')) {
            if (step === 'shooter') { newData.shooter = input; nextStep = 'blocker'; } else if (step === 'blocker') { newData.blocker = input; nextStep = 'rebound_team'; } else if (step === 'rebound_team') { if (input === 'none') nextStep = 'finish'; else { newData.rebounder = input; if (input === 'home' || input === 'away') newData.reboundTeamSide = input; nextStep = 'finish'; } }
        } else if (primaryAction.label.includes('Turnover')) {
            if (step === 'turnover_player') { newData.turnoverPlayer = input; nextStep = 'turnover_type'; } else if (step === 'turnover_type') { newData.turnoverType = input; if (['Bad Pass', 'Lost Ball'].includes(input)) nextStep = 'turnover_forcer'; else nextStep = 'finish'; } else if (step === 'turnover_forcer') { newData.turnoverForcer = input; nextStep = 'finish'; }
        } else if (primaryAction.label.includes('Steal')) {
            if (step === 'stealer') { newData.stealer = input; nextStep = 'victim'; } else if (step === 'victim') { newData.victim = input; nextStep = 'finish'; }
        } else if (primaryAction.label.includes('FT')) {
            if (step === 'ft_shooter') {
                newData.shooter = input;
                if (primaryAction.label.includes('Miss')) nextStep = 'rebound_team';
                else nextStep = 'assist';
            }
            else if (step === 'assist') { newData.assist = input; nextStep = 'finish'; }
            else if (step === 'rebound_team') { if (input === 'none') nextStep = 'finish'; else { newData.rebounder = input; if (input === 'home' || input === 'away') newData.reboundTeamSide = input; nextStep = 'finish'; } }
        } else if (primaryAction.label.includes('Sub')) {
            if (step === 'sub_out') { newData.subOut = input; nextStep = 'sub_in'; } else if (step === 'sub_in') { newData.subIn = input; nextStep = 'finish'; }
        } else if (primaryAction.label.includes('Jump Ball')) {
            if (step === 'jump_ball_contesters') { const updated = [...(newData.contesters || []), input]; if (!newData.contesters?.some((p: Player) => p.id === input.id)) newData.contesters = updated; if (updated.length >= 2) nextStep = 'jump_ball_winner'; else { nextStep = 'jump_ball_contesters'; setWorkflow({ ...workflowRef.current, data: newData }); return; } } else if (step === 'jump_ball_winner') { newData.jumpWinner = input; nextStep = 'finish'; }
        } else if (primaryAction.label.includes('Timeout')) {
            if (step === 'timeout_team') { newData.timeoutTeam = input; nextStep = 'finish'; }
        } else {
            if (step === 'foul_committer') { newData.foulCommitter = input; nextStep = 'foul_type'; }
            else if (step === 'foul_type') { newData.foulType = input; nextStep = 'victim'; }
            else if (step === 'victim') { newData.victim = input; nextStep = 'finish'; }
            else if (step === 'rebound') { newData.rebounder = input; nextStep = 'finish'; }
        }

        if (nextStep === 'finish') { commitWorkflow(newData, primaryAction); setWorkflow(initialWorkflowState); }
        else { setWorkflow({ ...workflowRef.current, step: nextStep as WorkflowStep, data: newData }); }
    }, []);

    const commitWorkflow = (data: any, primaryAction: Categorizer) => {
        const groupId = crypto.randomUUID();
        const tagsToAdd: Tag[] = [];
        const { timestamp, gameClock } = data;
        const currentGame = gameRef.current;

        const createTag = (label: string, cat: string, player: Player | null, descriptors: string[] = [], outcome?: string, shotType?: string): Tag => ({
            id: generateId() + Math.floor(Math.random() * 1000), label, category: cat, startTime: Math.max(0, timestamp - currentGame.leadTime), endTime: Math.min(videoStateRef.current.duration, timestamp + currentGame.lagTime),
            gameClock, period: activePeriodRef.current, player, lineup: currentGame.activeLineup, descriptors, note: '', groupId, outcome: outcome as any, shotType: shotType as any
        });

        if (primaryAction.label.includes('Sub')) {
            const outP = data.subOut; const inP = data.subIn;
            if (outP && inP) {
                const newLineup = currentGame.activeLineup.filter(id => id !== outP.id).concat(inP.id);
                dispatch({ type: 'UPDATE_LINEUP', payload: newLineup });
                const subTag = createTag('Sub', 'Other', inP);
                subTag.note = `Out: ${outP.number} ${outP.name}, In: ${inP.number} ${inP.name}`;
                subTag.descriptors = [`In: ${inP.number}`, `Out: ${outP.number}`];
                tagsToAdd.push(subTag);
                showToast(`Sub: #${outP.number} Out, #${inP.number} In`, "success");
            }
        } else {
            let primaryTag = createTag(primaryAction.label, primaryAction.category, null);
            if (primaryAction.label.includes('Make') || primaryAction.label.includes('Miss')) {
                primaryTag.player = data.shooter || null; primaryTag.outcome = primaryAction.label.includes('Make') ? 'make' : 'miss';
                if (primaryAction.label.includes('3pt')) primaryTag.descriptors.push('3pt');
                tagsToAdd.push(primaryTag);
                if (data.assist && data.assist !== 'none') tagsToAdd.push(createTag('Assist', 'Offense', data.assist));
                if (data.rebounder || data.reboundTeamSide) {
                    let isOff = false; let rebPlayer = null;
                    if (data.rebounder === 'team_off') isOff = true; else if (data.rebounder === 'team_def') isOff = false;
                    else if (typeof data.rebounder === 'string') isOff = data.reboundTeamSide === data.shooter?.team;
                    else { rebPlayer = data.rebounder; if (data.shooter) isOff = rebPlayer.team === data.shooter.team; }
                    tagsToAdd.push(createTag('Rebound', 'Defense', rebPlayer, isOff ? ['Offensive'] : ['Defensive']));
                }
            }
            else { primaryTag.player = data.foulCommitter || data.turnoverPlayer || data.stealer || data.rebounder || null; if (data.foulType) primaryTag.descriptors.push(data.foulType); if (data.turnoverType) primaryTag.descriptors.push(data.turnoverType); tagsToAdd.push(primaryTag); }
        }
        if (tagsToAdd.length > 0) dispatch({ type: 'ADD_TAGS_BATCH', payload: tagsToAdd });
    };

    const cancelWorkflow = useCallback(() => { setWorkflow(initialWorkflowState); setAmbiguousMatches(null); showToast("Action cancelled", "info"); }, []);

    const handleToggleLineup = (playerId: string) => {
        const currentLineup = game.activeLineup || [];
        const newLineup = currentLineup.includes(playerId) ? currentLineup.filter(id => id !== playerId) : [...currentLineup, playerId];
        dispatch({ type: 'UPDATE_LINEUP', payload: newLineup });
    };

    const handleSyncClock = useCallback(() => {
        const targetSeconds = parseGameClock(tempGameClock);
        const start = game.periodStarts?.[activePeriod.toString()] ?? 0;
        const currentImpliedSeconds = getPeriodLength(activePeriod, game) - (currentTime - start);

        // Offset = How much we need to subtract from the elapsed time to match target
        // CurrentCalc = Length - (Elapsed - OldOffset)
        // Target = Length - (Elapsed - NewOffset)
        // NewOffset = Target - Length + Elapsed

        const periodLength = getPeriodLength(activePeriod, game);
        const elapsed = currentTime - start;
        const newOffset = targetSeconds - periodLength + elapsed;

        const updates: any = {
            periodClockOffsets: {
                ...game.periodClockOffsets,
                [activePeriod.toString()]: newOffset
            }
        };

        dispatch({ type: 'UPDATE_GAME', payload: updates });
        if (!isGameClockRunning) setClockStopTime(currentTime);
        setIsClockSyncOpen(false);
        showToast(`Synced ${getPeriodLabel(activePeriod, game.regulationPeriods)} to ${formatGameClock(targetSeconds)}`, "success");
    }, [game.periodLength, game.periodStarts, game.periodClockOffsets, game.regulationPeriods, game.overtimeLength, activePeriod, tempGameClock, currentTime, isGameClockRunning]);

    const handleSetQuarterStart = useCallback(() => {
        dispatch({ type: 'UPDATE_GAME', payload: { periodStarts: { ...game.periodStarts, [activePeriod.toString()]: currentTime } } });
        if (videoStateRef.current.isPlaying) { setIsGameClockRunning(true); setClockStopTime(null); } else { setIsGameClockRunning(false); setClockStopTime(currentTime); }
        showToast(`${getPeriodLabel(activePeriod, game.regulationPeriods)} Start set to ${formatTime(currentTime)}`, "success");
    }, [game.periodStarts, game.regulationPeriods, activePeriod, currentTime]);

    const handleSetQuarterEnd = useCallback(() => {
        dispatch({ type: 'UPDATE_GAME', payload: { periodEnds: { ...game.periodEnds, [activePeriod.toString()]: currentTime } } });
        showToast(`${getPeriodLabel(activePeriod, game.regulationPeriods)} End set to ${formatTime(currentTime)}`, "success");
    }, [game.periodEnds, game.regulationPeriods, activePeriod, currentTime]);

    const handleClearQuarterBounds = useCallback(() => {
        const newStarts = { ...game.periodStarts }; delete newStarts[activePeriod.toString()];
        const newEnds = { ...game.periodEnds }; delete newEnds[activePeriod.toString()];
        dispatch({ type: 'UPDATE_GAME', payload: { periodStarts: newStarts, periodEnds: newEnds } });
        showToast(`Cleared ${getPeriodLabel(activePeriod, game.regulationPeriods)} boundaries`, "info");
    }, [game.periodStarts, game.periodEnds, game.regulationPeriods, activePeriod]);

    const handleJumpToGameClock = useCallback(() => {
        const periodStart = game.periodStarts?.[activePeriod.toString()];
        if (periodStart === undefined) { showToast(`${getPeriodLabel(activePeriod, game.regulationPeriods)} start not set. Please sync clock first.`, "error"); return; }
        const periodLength = getPeriodLength(activePeriod, game);
        handleSeek(Math.max(0, periodStart + (periodLength - parseGameClock(jumpTargetTime))));
        setIsJumpOpen(false);
        showToast(`Jumped to ${getPeriodLabel(activePeriod, game.regulationPeriods)} ${jumpTargetTime}`, "success");
    }, [game.periodStarts, game.periodLength, game.regulationPeriods, game.overtimeLength, activePeriod, jumpTargetTime]);

    const toggleFullScreen = useCallback(() => {
        const container = playerContainerRef.current;
        if (container) { if (!document.fullscreenElement) container.requestFullscreen().catch(console.error); else document.exitFullscreen(); }
    }, []);

    const togglePiP = useCallback(async () => {
        try { if (document.pictureInPictureElement) await document.exitPictureInPicture(); else if (videoRef.current) await videoRef.current.requestPictureInPicture(); } catch (error) { console.error("PiP failed", error); showToast("PiP failed or not supported", "error"); }
    }, []);

    const handleUpdateTagClock = useCallback((id: number, newClockStr: string) => dispatch({ type: 'UPDATE_TAG', payload: { id, gameClock: parseGameClock(newClockStr) } }), []);
    const handleUpdateTagPeriod = useCallback((id: number, newPeriod: number) => dispatch({ type: 'UPDATE_TAG', payload: { id, period: newPeriod } }), []);

    const handleSetTagLocation = useCallback((x: number, y: number) => {
        selectedTagsRef.current.forEach(id => { dispatch({ type: 'UPDATE_TAG', payload: { id, x, y } }); });
        setIsLocationModalOpen(false);
    }, []);

    const handleNewGame = useCallback(() => {
        if (game.tags.length > 0) {
            if (!confirm("Start a new project? Any unsaved changes will be lost.")) return;
        }
        dispatch({ type: 'NEW_GAME' });
        setVideoSrc(null);
        setPlaylists([]);
        setTelestratorPaths([]);
        setExportFileName('');
        setCurrentTime(0);
        showToast("New Project Started", "success");
    }, [game.tags.length, dispatch, setVideoSrc, setCurrentTime]);

    const handleSaveGame = () => { downloadFile(JSON.stringify(game, null, 2), `${game.name.replace(/\s+/g, '_')}_Project.json`); showToast("Project saved successfully", "success"); };
    const handleLoadGame = (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (file) { const reader = new FileReader(); reader.onload = (event) => { try { dispatch({ type: 'LOAD_GAME', payload: JSON.parse(event.target?.result as string) }); showToast("Project loaded successfully", "success"); } catch (err) { showToast("Failed to load project file", "error"); } }; reader.readAsText(file); e.target.value = ''; }
    };
    const handleLoadSample = () => { if (game.tags.length === 0 || confirm("Load sample game? Unsaved data will be lost.")) { dispatch({ type: 'LOAD_GAME', payload: getSampleGame() }); showToast("Sample game loaded", "success"); setIsSettingsOpen(false); } };
    const handleAddToPlaylist = (playlistId: string, tagId: number) => { setPlaylists(prev => prev.map(pl => pl.id === playlistId ? { ...pl, items: [...pl.items, { id: generateId().toString(), tagId, order: pl.items.length }] } : pl)); showToast("Added clip to playlist", "success"); };
    const handleRemovePlaylistItem = (playlistId: string, index: number) => setPlaylists(prev => prev.map(pl => pl.id === playlistId ? { ...pl, items: pl.items.filter((_, i) => i !== index) } : pl));
    const handleReorderPlaylistItem = (playlistId: string, fromIdx: number, toIdx: number) => setPlaylists(prev => prev.map(pl => pl.id === playlistId ? { ...pl, items: (() => { const items = [...pl.items]; const [moved] = items.splice(fromIdx, 1); items.splice(toIdx, 0, moved); return items; })() } : pl));
    const handleSetFilter = useCallback((filter: FilterState) => { if (JSON.stringify(filter) === JSON.stringify(filterState)) { setFilterState({}); showToast("Filter cleared", "info"); return; } setFilterState(filter); setView('tagger'); showToast("Filter applied to Timeline", "info"); }, [filterState]);

    const handlePlayPlaylist = useCallback((playlistId: string) => {
        let ids: number[] = [];
        if (playlistId.startsWith('auto:')) { /* auto logic */ } else { const pl = playlists.find(p => p.id === playlistId); if (pl) ids = pl.items.map(i => i.tagId); }
        if (ids.length > 0) { const firstTag = game.tags.filter(t => ids.includes(t.id)).sort((a, b) => a.startTime - b.startTime)[0]; setFilterState({ includedTagIds: ids }); setView('tagger'); if (firstTag) handleSeek(firstTag.startTime); setIsPlaying(true); showToast("Playing Reel", "success"); } else showToast("Playlist is empty", "info");
    }, [game.tags, playlists]);

    const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => { const file = event.target.files?.[0]; if (file) { setVideoSrc(URL.createObjectURL(file)); dispatch({ type: 'UPDATE_GAME', payload: { videoFileName: file.name } }); setExportFileName(file.name.split('.')[0]); setIsPlaying(false); setCurrentTime(0); broadcastChannel.postMessage({ type: 'LOAD', payload: URL.createObjectURL(file) }); showToast("Video loaded successfully", "success"); } };
    const handleDrop = (event: React.DragEvent) => { event.preventDefault(); const file = event.dataTransfer.files?.[0]; if (file && file.type.startsWith('video/')) { setVideoSrc(URL.createObjectURL(file)); dispatch({ type: 'UPDATE_GAME', payload: { videoFileName: file.name } }); setExportFileName(file.name.split('.')[0]); setIsPlaying(false); setCurrentTime(0); broadcastChannel.postMessage({ type: 'LOAD', payload: URL.createObjectURL(file) }); showToast("Video loaded successfully", "success"); } };
    const handleDragOver = (event: React.DragEvent) => event.preventDefault();
    const handleJumpEvent = (direction: 'prev' | 'next') => { if (game.tags.length === 0) return; const sorted = [...game.tags].sort((a, b) => a.startTime - b.startTime); let targetTime = currentTime; if (direction === 'next') { const nextTag = sorted.find(t => t.startTime > currentTime + 0.5); if (nextTag) targetTime = nextTag.startTime; } else { const prevTag = [...sorted].reverse().find(t => t.startTime < currentTime - 0.5); if (prevTag) targetTime = prevTag.startTime; } if (targetTime !== currentTime) handleSeek(targetTime); };

    const handleAnnotatorSnapshot = async () => {
        if (!annotatorVideoRef.current) return;
        const video = annotatorVideoRef.current;
        const svg = document.getElementById('telestrator-svg-layer');
        if (!svg) { showToast("Could not find drawing layer", "error"); return; }

        try {
            const canvas = document.createElement('canvas'); canvas.width = video.videoWidth; canvas.height = video.videoHeight;
            const ctx = canvas.getContext('2d'); if (!ctx) return;
            ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
            const serializer = new XMLSerializer(); const svgBlob = new Blob([serializer.serializeToString(svg)], { type: 'image/svg+xml;charset=utf-8' });
            const svgUrl = URL.createObjectURL(svgBlob);
            const img = new Image(); img.onload = () => { ctx.drawImage(img, 0, 0); URL.revokeObjectURL(svgUrl); const a = document.createElement('a'); a.download = `Snapshot.png`; a.href = canvas.toDataURL('image/png'); document.body.appendChild(a); a.click(); document.body.removeChild(a); showToast("Snapshot saved", "success"); }; img.src = svgUrl;
        } catch (e) { showToast("Snapshot failed", "error"); }
    };

    const handleRenderVideo = async () => {
        if (!videoRef.current || !videoSrc) return;
        setIsExportModalOpen(false); setIsRendering(true); renderingRef.current = true; setRenderProgress(0);
        const video = videoRef.current; const wasPlaying = !video.paused; const originalTime = video.currentTime; video.pause();
        const canvas = document.createElement('canvas'); canvas.width = 1280; canvas.height = 720; const ctx = canvas.getContext('2d');
        if (!ctx) { setIsRendering(false); return; }

        const stream = canvas.captureStream(30);
        // @ts-ignore
        if (video.captureStream) { const videoStream = video.captureStream(); if (videoStream.getAudioTracks().length > 0) stream.addTrack(videoStream.getAudioTracks()[0]); }
        const recorder = new MediaRecorder(stream, { mimeType: 'video/webm;codecs=h264', videoBitsPerSecond: 5000000 });
        const chunks: Blob[] = [];
        recorder.ondataavailable = e => { if (e.data.size > 0) chunks.push(e.data); };
        recorder.onstop = () => { downloadFile(new Blob(chunks, { type: 'video/webm' }), `${exportFileName || 'video'}_burned.mp4`); setIsRendering(false); video.currentTime = originalTime; if (wasPlaying) video.play(); showToast("Video rendered successfully", "success"); };
        recorder.start(); video.currentTime = 0; await video.play();
        const renderLoop = () => { if (!renderingRef.current || video.ended || video.paused) { if (renderingRef.current && video.ended) { recorder.stop(); renderingRef.current = false; } return; } drawFrameOnCanvas(ctx, video, telestratorPaths, video.currentTime); setRenderProgress((video.currentTime / video.duration) * 100); requestAnimationFrame(renderLoop); };
        renderLoop();
    };

    const cancelRendering = () => { renderingRef.current = false; setIsRendering(false); if (videoRef.current) videoRef.current.pause(); };

    useEffect(() => {
        const vRef = view === 'tagger' ? videoRef.current : (view === 'annotator' ? annotatorVideoRef.current : null);
        if (vRef && videoSrc) { if (Math.abs(vRef.currentTime - currentTime) > 0.5) vRef.currentTime = currentTime; if (isPlaying && vRef.paused) vRef.play().catch(() => setIsPlaying(false)); else if (!isPlaying && !vRef.paused) vRef.pause(); vRef.muted = isMuted; }
    }, [view, isPlaying, videoSrc, isMuted]);

    useEffect(() => { if (videoSrc) return; let interval: number; if (isPlaying) { interval = window.setInterval(() => { setCurrentTime(prev => { if (prev >= duration) { setIsPlaying(false); return prev; } return prev + 0.1; }); }, 100); } return () => clearInterval(interval); }, [isPlaying, duration, videoSrc]);

    const handleSelectTag = useCallback((id: number, multi: boolean) => { if (id === 0) { setSelectedTagIds([]); setSidebarTab('console'); return; } if (multi) { setSelectedTagIds(prev => prev.includes(id) ? prev : [...prev, id]); setSidebarTab('editor'); } else { setSelectedTagIds([id]); setSidebarTab('editor'); } }, []);
    const handleMultiSelect = (ids: number[]) => { setSelectedTagIds(ids); if (ids.length > 0) setSidebarTab('editor'); else setSidebarTab('console'); };
    const handleUpdateTagRange = useCallback((id: number, start: number, end: number) => { dispatch({ type: 'UPDATE_TAG', payload: { id, startTime: start, endTime: end } }); }, []);
    const handleUpdateTagsBatch = useCallback((updates: { id: number, start: number, end: number }[]) => { dispatch({ type: 'UPDATE_TAGS_BATCH', payload: updates.map(u => ({ id: u.id, changes: { startTime: u.start, endTime: u.end } })) }); }, []);
    const handleAddDescriptor = useCallback((descriptor: Descriptor) => { if (selectedTagsRef.current.length > 0) { selectedTagsRef.current.forEach(id => { const tag = game.tags.find(t => t.id === id); if (tag) { let updated = [...tag.descriptors]; if (updated.includes(descriptor.label)) updated = updated.filter(d => d !== descriptor.label); else updated.push(descriptor.label); dispatch({ type: 'UPDATE_TAG', payload: { id, descriptors: updated } }); } }); } }, [game.tags]);
    const handleAssignPlayer = useCallback((player: Player) => { if (selectedTagsRef.current.length > 0) { selectedTagsRef.current.forEach(id => { dispatch({ type: 'UPDATE_TAG', payload: { id, player } }); }); showToast(`Assigned to #${player.number} ${player.name}`, "success"); } else showToast("Select a tag first to assign player", "info"); }, []);

    const handlePerformExport = () => {
        const filenameBase = exportFileName.trim() || game.name.replace(/\s+/g, '_');
        let tagsToExport = game.tags;
        if (Object.keys(filterState).length > 0 && exportConfig.type !== 'playlists') { /* filter logic */ }
        if (exportConfig.type === 'xml') { if (!game.videoFileName && !confirm("No video filename found. Default to 'video.mp4'?")) return; downloadFile(generatePremiereXML(game, tagsToExport, duration, game.videoFileName || 'video.mp4'), `${filenameBase}_Highlights.xml`); } else if (exportConfig.type === 'box') { downloadFile(generateBoxScoreCSV(game, exportConfig.scope), `${filenameBase}_BoxScore_${exportConfig.scope}.csv`); } else if (exportConfig.type === 'pbp') { downloadFile(generatePlayByPlayCSV(game, exportConfig.scope), `${filenameBase}_PlayByPlay_${exportConfig.scope}.csv`); } else if (exportConfig.type === 'playlists') { downloadFile(generatePlaylistsCSV(game, playlists), `${filenameBase}_Playlists.csv`); } else if (exportConfig.type === 'analytics') { downloadFile(generateAnalyticsCSV(game), `${filenameBase}_Analytics.csv`); } else { downloadFile(generateCSVBlob(game, tagsToExport), `${filenameBase}_RawData.csv`); }
        showToast("Export completed successfully", "success"); setIsExportModalOpen(false);
    };

    const handleScrubberMove = (e: React.MouseEvent) => { if (!scrubberRef.current || !duration) return; const rect = scrubberRef.current.getBoundingClientRect(); setScrubHover({ x: e.clientX - rect.left, time: Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width)) * duration }); };
    const handleScrubberLeave = () => setScrubHover(null);

    useEffect(() => {
        if (isPlaying && !isGameClockRunning && !workflowRef.current.active) {
            setIsGameClockRunning(true);
            setClockStopTime(null);
        }
    }, [isPlaying]);

    const { playerInputBuffer } = useAppShortcuts({
        gameRef,
        videoStateRef,
        workflowRef,
        selectedTagsRef,
        activePeriodRef,
        dispatch,
        togglePlay,
        toggleMute,
        toggleFullScreen,
        stepFrame,
        setZoom,
        startWorkflow,
        handleWorkflowInput,
        setSidebarTab,
        setSelectedTagIds,
        showToast,
        setAmbiguousMatches,
        handleSetQuarterStart,
        handleSetQuarterEnd,
        handleClearQuarterBounds,
        setTempGameClock,
        setIsClockSyncOpen,
        setIsJumpOpen,
        formatGameClock,
        getGameClockSeconds,
        cancelWorkflow,
        handleSeek
    });

    const handleExitPresenterView = () => setView('tagger');

    const handleNextPeriod = () => {
        if (activePeriod < game.periods) {
            setActivePeriod(activePeriod + 1);
        } else {
            // Confirm Add Overtime
            if (confirm("Start Overtime Period?")) {
                dispatch({
                    type: 'UPDATE_GAME',
                    payload: {
                        periods: game.periods + 1,
                        // Automatically set start time of new OT period to current video time
                        periodStarts: { ...game.periodStarts, [(game.periods + 1).toString()]: currentTime }
                    }
                });
                setActivePeriod(game.periods + 1);
                setIsGameClockRunning(true);
                setClockStopTime(null);
                showToast("Overtime Started", "success");
            }
        }
    };

    if (view === 'presenter') return <div className="flex flex-col h-screen bg-black overflow-hidden font-sans" onContextMenu={(e) => e.preventDefault()}><PresenterView game={game} videoSrc={videoSrc} onExit={handleExitPresenterView} /></div>;

    return (
        <div className="flex flex-col h-screen bg-black text-zinc-100 overflow-hidden font-sans relative" onContextMenu={(e) => e.preventDefault()}>
            {isRendering && (
                <div className="fixed inset-0 z-[100] bg-black/90 flex flex-col items-center justify-center p-8 backdrop-blur-md">
                    <Loader2 size={48} className="text-orange-500 animate-spin mb-6" />
                    <h2 className="text-2xl font-bold text-white mb-2">Rendering Video...</h2>
                    <div className="w-full max-w-md h-2 bg-zinc-800 rounded-full overflow-hidden mb-8"><div className="h-full bg-orange-600 transition-all duration-200" style={{ width: `${renderProgress}%` }}></div></div>
                    <button onClick={cancelRendering} className="flex items-center gap-2 px-6 py-3 bg-red-900/30 text-red-400 border border-red-900/50 rounded-lg hover:bg-red-900/50 transition-colors font-bold"><StopCircle size={20} /> Cancel</button>
                </div>
            )}
            {playerInputBuffer && <div className="fixed top-20 right-1/2 translate-x-1/2 z-[100] bg-black/80 text-white px-6 py-4 rounded-xl border border-zinc-700 shadow-2xl flex flex-col items-center animate-in fade-in zoom-in-95 duration-100 pointer-events-none"><span className="text-[10px] uppercase font-bold text-zinc-500 tracking-widest">Player Input</span><span className="text-4xl font-mono font-black text-brand-500 tracking-tighter">#{playerInputBuffer}</span></div>}
            {showSplash && <SplashScreen onFinish={() => setShowSplash(false)} isLoading={isLoading} />}
            <ToastContainer toasts={toasts} onDismiss={(id) => setToasts(prev => prev.filter(t => t.id !== id))} />
            <input ref={projectInputRef} type="file" accept=".json" className="hidden" onChange={handleLoadGame} />
            <SettingsModal isOpen={isSettingsOpen} onClose={() => setIsSettingsOpen(false)} game={game} dispatch={dispatch} onLoadSample={handleLoadSample} defaultView={defaultView} onSetDefaultView={setDefaultView} enabledViews={enabledViews} onSetEnabledViews={setEnabledViews} />

            <Header
                game={game} view={view} setView={setView} canUndo={canUndo} canRedo={canRedo} dispatch={dispatch}
                installPrompt={installPrompt} handleInstallClick={handleInstallClick} projectInputRef={projectInputRef}
                handleSaveGame={handleSaveGame} setIsExportModalOpen={setIsExportModalOpen} setExportFileName={setExportFileName}
                handleOpenPresenter={handleOpenPresenter} setIsShortcutsOpen={setIsShortcutsOpen} setIsSettingsOpen={setIsSettingsOpen}
                visibleViews={['tagger', 'analytics', 'matrix', 'playlists', 'annotator', 'comparison', 'presenter'].filter(v => enabledViews.includes(v))}
                handleNewGame={handleNewGame}
            />

            <main className="flex-1 overflow-hidden relative">
                <React.Suspense fallback={<div className="flex items-center justify-center h-full"><Loader2 className="animate-spin text-orange-500" /></div>}>
                    {view === 'tagger' && (
                        <ResizableSplit direction="vertical" initialSplit={vSplit} onChange={setVSplit} minSize={50} className="bg-zinc-950">
                            <div className="h-full overflow-hidden">
                                <ResizableSplit direction="horizontal" initialSplit={hSplit} onChange={setHSplit} minSize={300}>
                                    <div ref={playerContainerRef} className="h-full flex flex-col bg-zinc-950 min-w-0 border-r border-zinc-800 relative group/player">
                                        <div className="absolute inset-0 bg-black flex items-center justify-center overflow-hidden" onDrop={handleDrop} onDragOver={handleDragOver}>
                                            {videoSrc ? (<video ref={videoRef} src={videoSrc} className="max-w-full max-h-full w-auto h-auto object-contain" onTimeUpdate={handleTimeUpdate} onLoadedMetadata={handleLoadedMetadata} onClick={togglePlay} onError={() => showToast("Video format not supported", "error")} muted={isMuted} />) : (<div className="flex flex-col items-center justify-center h-full w-full bg-zinc-900/20"><EmptyStateIllustration className="w-64 h-64 text-zinc-800 mb-6" /><div className="flex flex-col items-center pointer-events-auto"><h3 className="text-xl font-bold text-zinc-500 mb-2">Ready to Analyze?</h3><p className="text-sm text-zinc-600 mb-6">Drop a video file here or select one to begin.</p><label className="cursor-pointer bg-brand-600 hover:bg-brand-500 text-white px-6 py-3 rounded-lg text-sm font-bold transition-all shadow-lg hover:shadow-brand-900/20 flex items-center gap-2 group"><Upload size={18} className="group-hover:scale-110 transition-transform" /> Select Video File <input type="file" accept="video/*" className="hidden" onChange={handleFileSelect} /></label></div></div>)}
                                        </div>

                                        {/* Scoreboard Overlay */}
                                        <div className="absolute top-4 left-4 z-40 transition-opacity duration-300 flex items-start gap-4 pointer-events-none">
                                            <div className="pointer-events-auto flex items-center gap-3">
                                                <div className="flex items-center bg-black/60 backdrop-blur-md px-3 py-1.5 rounded-lg border border-white/10 shadow-lg">
                                                    <div className="flex items-center gap-2 border-r border-white/10 pr-3 mr-3"><span className="text-[10px] font-bold uppercase tracking-wider max-w-[60px] truncate text-right" style={{ color: game.homeTeamColor }}>{game.homeTeamName}</span><span className="font-mono text-xl font-black text-white leading-none">{currentScore.home}</span></div>
                                                    <div className="flex items-center gap-2"><span className="font-mono text-xl font-black text-white leading-none">{currentScore.away}</span><span className="text-[10px] font-bold uppercase tracking-wider max-w-[60px] truncate text-left" style={{ color: game.awayTeamColor }}>{game.awayTeamName}</span></div>
                                                </div>
                                            </div>
                                        </div>


                                        <div className="absolute top-4 right-4 z-40 transition-opacity duration-300 pointer-events-none select-none">
                                            <div className="pointer-events-auto bg-black/80 backdrop-blur-md rounded-lg border border-white/10 shadow-[0_4px_16px_rgba(0,0,0,0.5)] flex flex-col p-1 gap-1 w-fit">
                                                {/* Top Row: Period & Clock */}
                                                <div className="flex items-center gap-1">
                                                    {/* Period Control */}
                                                    <div className="flex flex-col items-center justify-center bg-white/5 rounded px-1 py-0.5 border border-white/5 h-full">
                                                        <span className="text-[8px] text-zinc-500 font-bold uppercase tracking-widest mb-px">Per</span>
                                                        <div className="flex items-center gap-0.5">
                                                            <button onClick={() => setActivePeriod(Math.max(1, activePeriod - 1))} className="p-0.5 hover:text-white text-zinc-500 hover:bg-white/10 rounded transition-colors"><ChevronLeft size={10} /></button>
                                                            <span className="text-xs font-black text-white w-4 text-center">{getPeriodLabel(activePeriod, game.regulationPeriods).replace('Q', '')}</span>
                                                            <button onClick={handleNextPeriod} className="p-0.5 hover:text-white text-zinc-500 hover:bg-white/10 rounded transition-colors"><ChevronRight size={10} /></button>
                                                        </div>
                                                    </div>

                                                    {/* Clock Display */}
                                                    <div className="flex flex-col items-center justify-center bg-black/40 rounded px-1 py-0.5 border border-white/10 relative overflow-hidden">
                                                        <GameClockInput
                                                            className={`text-lg font-mono font-black tracking-normal bg-transparent text-center w-[50px] outline-none border-none focus:text-brand-500 transition-all p-0 leading-none ${!isGameClockRunning ? 'text-red-500 drop-shadow-[0_0_8px_rgba(239,68,68,0.5)]' : 'text-white'}`}
                                                            value={getGameClockSeconds((!isGameClockRunning && clockStopTime !== null) ? clockStopTime : currentTime, activePeriod, game)}
                                                            onChange={(newClockSeconds: number) => {
                                                                const targetSeconds = newClockSeconds;
                                                                const start = game.periodStarts?.[activePeriod.toString()] ?? 0;
                                                                const periodLength = getPeriodLength(activePeriod, game);
                                                                const elapsed = currentTime - start;
                                                                const newOffset = targetSeconds - periodLength + elapsed;

                                                                const updates: any = {
                                                                    periodClockOffsets: {
                                                                        ...game.periodClockOffsets,
                                                                        [activePeriod.toString()]: newOffset
                                                                    }
                                                                };
                                                                dispatch({ type: 'UPDATE_GAME', payload: updates });
                                                                showToast(`Synced ${getPeriodLabel(activePeriod, game.regulationPeriods)} to ${formatGameClock(newClockSeconds)}`, "success");
                                                            }}
                                                        />
                                                    </div>
                                                </div>

                                                {/* Bottom Row: Utility Buttons */}
                                                <div className="grid grid-cols-2 gap-1 relative">
                                                    <button
                                                        onClick={() => { setTempGameClock(formatGameClock(getGameClockSeconds(currentTime, activePeriod, game))); setIsClockSyncOpen(!isClockSyncOpen); setIsJumpOpen(false); }}
                                                        className={`py-1 px-1 rounded text-[8px] font-bold uppercase tracking-wider flex items-center justify-center gap-1 transition-colors ${isClockSyncOpen ? 'bg-brand-600 text-white' : 'bg-zinc-800 text-zinc-400 hover:bg-zinc-700 hover:text-white'}`}
                                                        title="Sync Clock"
                                                    >
                                                        <Clock size={8} /> Sync
                                                    </button>
                                                    <button
                                                        onClick={() => { setJumpTargetTime(formatGameClock(getPeriodLength(activePeriod, game))); setIsJumpOpen(!isJumpOpen); setIsClockSyncOpen(false); }}
                                                        className={`py-1 px-1 rounded text-[8px] font-bold uppercase tracking-wider flex items-center justify-center gap-1 transition-colors ${isJumpOpen ? 'bg-zinc-600 text-white' : 'bg-zinc-800 text-zinc-400 hover:bg-zinc-700 hover:text-white'}`}
                                                        title="Jump to Time"
                                                    >
                                                        <CornerUpRight size={8} /> Jump
                                                    </button>

                                                    {/* Popovers - Anchored relative to the buttons container */}
                                                    {isClockSyncOpen && (
                                                        <div className="absolute top-full left-0 mt-1 w-full bg-zinc-900 border border-zinc-700 p-1.5 rounded shadow-xl flex items-center gap-1 z-50 animate-in fade-in zoom-in-95 duration-100">
                                                            <input
                                                                className="bg-black border border-zinc-700 text-white font-mono text-xs p-1 w-full text-center rounded outline-none focus:border-brand-500"
                                                                value={tempGameClock}
                                                                onChange={(e) => setTempGameClock(e.target.value)}
                                                                placeholder="MM:SS"
                                                                autoFocus
                                                                onKeyDown={(e) => e.key === 'Enter' && handleSyncClock()}
                                                            />
                                                            <button onClick={handleSyncClock} className="bg-brand-600 hover:bg-brand-500 text-white p-1 rounded shrink-0">
                                                                <Check size={12} />
                                                            </button>
                                                        </div>
                                                    )}

                                                    {isJumpOpen && (
                                                        <div className="absolute top-full right-0 mt-1 w-[140px] bg-zinc-900 border border-zinc-700 p-2 rounded shadow-xl flex flex-col gap-1.5 z-50 animate-in fade-in zoom-in-95 duration-100">
                                                            <div className="text-[8px] uppercase font-bold text-zinc-500 tracking-widest text-center">Jump to {getPeriodLabel(activePeriod, game.regulationPeriods)} Clock</div>
                                                            <div className="flex items-center gap-1">
                                                                <GameClockInput
                                                                    className="bg-black border border-zinc-700 text-white font-mono text-xs p-1 w-full text-center rounded outline-none focus:border-brand-500"
                                                                    value={parseGameClock(jumpTargetTime)}
                                                                    onChange={(secs: number) => setJumpTargetTime(formatGameClock(secs))}
                                                                    placeholder="MM:SS"
                                                                    autoFocus
                                                                    onKeyDown={(e: any) => e.key === 'Enter' && handleJumpToGameClock()}
                                                                />
                                                                <button onClick={handleJumpToGameClock} className="bg-zinc-700 hover:bg-zinc-600 text-white p-1 rounded shrink-0 font-bold text-[10px]">GO</button>
                                                            </div>
                                                        </div>
                                                    )}
                                                </div>
                                            </div>
                                        </div>

                                        {/* Controls Overlay */}
                                        {videoSrc && (
                                            <div className="absolute bottom-0 left-0 right-0 z-40 bg-gradient-to-t from-black/90 via-black/60 to-transparent pt-16 pb-4 px-6 flex flex-col gap-3 transition-opacity duration-300 opacity-0 group-hover/player:opacity-100 pointer-events-none">
                                                <div className="flex items-center gap-4 pointer-events-auto">
                                                    <div className="font-mono font-bold text-sm text-white tabular-nums tracking-tight"><TimeInput className="bg-transparent border-b border-transparent hover:border-white/20 focus:border-orange-500 outline-none w-16 text-center cursor-text transition-colors" value={currentTime} onChange={(val: number) => handleSeek(val)} placeholder="00:00" /></div>
                                                    <div ref={scrubberRef} className="flex-1 relative h-1.5 bg-white/20 hover:bg-white/30 rounded-full cursor-pointer group/slider transition-all" onMouseMove={handleScrubberMove} onMouseLeave={handleScrubberLeave} onClick={(e) => { if (!scrubberRef.current || !duration) return; const rect = scrubberRef.current.getBoundingClientRect(); handleSeek(Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width)) * duration); }}>
                                                        <div className="absolute top-0 bottom-0 left-0 bg-brand-500 w-0 rounded-full shadow-[0_0_10px_rgba(249,115,22,0.5)]" style={{ width: `${(currentTime / (duration || 1)) * 100}%` }}></div>
                                                        {scrubHover && (videoSrc ? <VideoPreviewTooltip src={videoSrc} time={scrubHover.time} x={scrubHover.x} /> : <div className="absolute bottom-4 transform -translate-x-1/2 bg-black text-white text-[10px] font-mono font-bold px-2 py-1 rounded border border-zinc-800 shadow-xl pointer-events-none z-50" style={{ left: scrubHover.x }}>{formatTime(scrubHover.time)}<div className="absolute top-full left-1/2 -translate-x-1/2 -mt-[1px] border-4 border-transparent border-t-black"></div></div>)}
                                                    </div>
                                                    <div className="text-xs text-white/60 font-mono font-medium flex flex-col items-end leading-none"><span>{formatTime(duration)}</span><span className="text-[9px] opacity-60">Fr: {currentFrame}</span></div>
                                                </div>
                                                <div className="flex items-center justify-between pointer-events-auto">
                                                    <div className="flex items-center gap-4">
                                                        <div className="flex items-center gap-2"><button onClick={() => stepFrame(-1)} className="p-2 rounded-full text-white/70 hover:text-white hover:bg-white/10"><ChevronLeft size={20} /></button><button onClick={togglePlay} className={`p-3 rounded-full ${isPlaying ? 'bg-white/10 text-orange-500' : 'bg-white text-black hover:bg-zinc-200'} transition-all shadow-lg`}>{isPlaying ? <Pause size={20} fill="currentColor" /> : <Play size={20} fill="currentColor" className="ml-0.5" />}</button><button onClick={() => stepFrame(1)} className="p-2 rounded-full text-white/70 hover:text-white hover:bg-white/10"><ChevronRight size={20} /></button></div>
                                                        <div className="w-px h-6 bg-white/10"></div>
                                                        <div className="flex items-center gap-1"><button onClick={handleSetQuarterStart} className={`w-8 h-8 rounded flex items-center justify-center font-bold font-mono text-xs transition-colors ${game.periodStarts?.[activePeriod.toString()] !== undefined ? 'text-brand-500 bg-brand-500/10 border border-brand-500/30' : 'text-white/50 hover:text-white hover:bg-white/10'}`} title="Set Quarter Start (I)"><span>[</span></button><button onClick={handleSetQuarterEnd} className={`w-8 h-8 rounded flex items-center justify-center font-bold font-mono text-xs transition-colors ${game.periodEnds?.[activePeriod.toString()] !== undefined ? 'text-brand-500 bg-brand-500/10 border border-brand-500/30' : 'text-white/50 hover:text-white hover:bg-white/10'}`} title="Set Quarter End (O)"><span>]</span></button>{(game.periodStarts?.[activePeriod.toString()] !== undefined || game.periodEnds?.[activePeriod.toString()] !== undefined) && <button onClick={handleClearQuarterBounds} className="w-8 h-8 rounded flex items-center justify-center text-white/40 hover:text-red-400 hover:bg-white/5 transition-colors" title="Clear Q Bounds (Alt+X)"><X size={14} /></button>}</div>
                                                    </div>
                                                    <div className="flex items-center gap-3">
                                                        <div className="relative"><button onClick={() => setIsSpeedMenuOpen(!isSpeedMenuOpen)} className="flex items-center gap-1 p-2 rounded text-white/60 hover:text-white hover:bg-white/10 transition-colors" title="Playback Speed"><Gauge size={18} /><span className="text-[10px] font-mono font-bold w-6 text-center">{playbackRate}x</span></button>{isSpeedMenuOpen && <><div className="fixed inset-0 z-40" onClick={() => setIsSpeedMenuOpen(false)}></div><div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 bg-zinc-900 border border-zinc-800 rounded shadow-xl py-1 flex flex-col z-50 min-w-[60px]">{[0.25, 0.5, 0.75, 1, 1.25, 1.5, 2].map(rate => (<button key={rate} onClick={() => { setPlaybackRate(rate); setIsSpeedMenuOpen(false); }} className={`px-3 py-1.5 text-xs font-bold hover:bg-zinc-800 text-center ${playbackRate === rate ? 'text-orange-500' : 'text-zinc-400'}`}>{rate}x</button>))}</div></>}</div>
                                                        <div className="relative"><button onClick={() => setIsFpsMenuOpen(!isFpsMenuOpen)} className="flex items-center gap-1 p-2 rounded text-white/60 hover:text-white hover:bg-white/10 transition-colors" title="Video FPS"><Film size={18} /><span className="text-[10px] font-mono font-bold w-6 text-center">{fps}</span></button>{isFpsMenuOpen && <><div className="fixed inset-0 z-40" onClick={() => setIsFpsMenuOpen(false)}></div><div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 bg-zinc-900 border border-zinc-800 rounded shadow-xl py-1 flex flex-col z-50 min-w-[80px]">{[24, 25, 30, 50, 60].map(val => (<button key={val} onClick={() => { setFps(val); setIsFpsMenuOpen(false); }} className={`px-3 py-1.5 text-xs font-bold hover:bg-zinc-800 text-center ${fps === val ? 'text-orange-500' : 'text-zinc-400'}`}>{val} FPS</button>))}</div></>}</div>
                                                        <button onClick={toggleMute} className="p-2 rounded text-white/60 hover:text-white hover:bg-white/10" title="Mute (m)">{isMuted ? <VolumeX size={18} /> : <Volume2 size={18} />}</button>
                                                        <button onClick={togglePiP} className="p-2 rounded text-white/60 hover:text-white hover:bg-white/10" title="Picture in Picture"><PictureInPicture size={18} /></button>
                                                        <button onClick={toggleFullScreen} className="p-2 rounded text-white/60 hover:text-white hover:bg-white/10" title="Full Screen (f)"><Maximize size={18} /></button>
                                                    </div>
                                                </div>
                                            </div>
                                        )}
                                    </div>

                                    <Sidebar
                                        sidebarTab={sidebarTab}
                                        setSidebarTab={setSidebarTab}
                                        workflow={workflow}
                                        game={game}
                                        selectedTagIds={selectedTagIds}
                                        dispatch={dispatch}
                                        handleWorkflowInput={handleWorkflowInput}
                                        startWorkflow={startWorkflow}
                                        cancelWorkflow={cancelWorkflow}
                                        handleAssignPlayer={handleAssignPlayer}
                                        handleAddDescriptor={handleAddDescriptor}
                                        handleUpdateTagClock={handleUpdateTagClock}
                                        handleUpdateTagPeriod={handleUpdateTagPeriod}
                                        handleSetTagLocation={handleSetTagLocation}
                                        activePeriod={activePeriod}
                                        ambiguousMatches={ambiguousMatches}
                                        resolveAmbiguity={resolveAmbiguity}
                                    />
                                </ResizableSplit>
                            </div>
                            <div className="h-full min-h-0 bg-zinc-950">
                                <Timeline tags={game.tags} players={game.players} duration={duration} currentTime={currentTime} selectedTagIds={selectedTagIds} onSeek={handleSeek} onSelectTag={handleSelectTag} onMultiSelect={handleMultiSelect} onUpdateTagRange={handleUpdateTagRange} onUpdateTagsBatch={handleUpdateTagsBatch} zoom={zoom} setZoom={setZoom} colorMode={colorMode} grouping={grouping} setGrouping={setGrouping} filter={filterState} onClearFilter={() => setFilterState({})} scrollRequest={scrollRequest} periodStarts={game.periodStarts || {}} periodEnds={game.periodEnds || {}} activePeriod={activePeriod} totalPeriods={game.periods} regulationPeriods={game.regulationPeriods} videoSrc={videoSrc} isCollapsed={isTimelineCollapsed} onToggleCollapse={handleToggleTimelineCollapse} />
                            </div>
                        </ResizableSplit>
                    )}

                    {view === 'annotator' && (
                        <div className="flex flex-col h-full relative bg-zinc-900">
                            <div className="h-12 bg-zinc-950 border-b border-zinc-800 flex items-center justify-between px-4 shrink-0">
                                <h2 className="text-sm font-bold uppercase tracking-widest text-zinc-400 flex items-center gap-2"><PenTool size={16} /> Annotator Mode</h2>
                                <div className="text-xs text-zinc-500">Draw on the video to create telestrations. Captures are auto-saved to the session.</div>
                            </div>
                            <div className="flex-1 flex items-center justify-center p-8 relative overflow-hidden">
                                <div className="relative w-full max-w-6xl max-h-[85vh] aspect-video bg-black rounded-lg shadow-2xl border border-zinc-800">
                                    {videoSrc && (<video ref={annotatorVideoRef} src={videoSrc} className="w-full h-full object-contain rounded-lg" onLoadedMetadata={handleLoadedMetadata} onClick={togglePlay} muted={isMuted} />)}
                                    <Telestrator width={1280} height={720} isDrawing={true} onClose={() => { }} paths={telestratorPaths} setPaths={setTelestratorPaths} redoStack={telestratorRedoStack} setRedoStack={setTelestratorRedoStack} onSnapshot={handleAnnotatorSnapshot} currentTime={currentTime} />
                                </div>
                            </div>
                            <div className="h-24 border-t border-zinc-800 bg-zinc-950 relative group">
                                <div className="absolute top-0 bottom-0 left-0 w-96 border-r border-zinc-800 bg-zinc-950 flex items-center justify-center gap-4 z-30 px-2">
                                    <button onClick={() => handleJumpEvent('prev')} className="p-2 rounded bg-zinc-900 border border-zinc-800 hover:bg-zinc-800 text-zinc-400 hover:text-white" title="Previous Event"><SkipBack size={16} /></button>
                                    <div className="flex items-center gap-1 bg-zinc-900 border border-zinc-800 rounded p-1"><button onClick={() => stepFrame(-1)} className="p-1 hover:text-white text-zinc-500" title="-1 Frame"><ChevronLeft size={14} /></button></div>
                                    <div className="flex flex-col items-center px-2"><button onClick={togglePlay} className="p-3 rounded-full bg-brand-600 hover:bg-brand-500 text-white shadow-lg shadow-brand-900/20">{isPlaying ? <Pause size={20} fill="currentColor" /> : <Play size={20} fill="currentColor" />}</button></div>
                                    <div className="flex items-center gap-1 bg-zinc-900 border border-zinc-800 rounded p-1"><button onClick={() => stepFrame(1)} className="p-1 hover:text-white text-zinc-500" title="+1 Frame"><ChevronRight size={14} /></button></div>
                                    <button onClick={() => handleJumpEvent('next')} className="p-2 rounded bg-zinc-900 border border-zinc-800 hover:bg-zinc-800 text-zinc-400 hover:text-white" title="Next Event"><SkipForward size={16} /></button>
                                </div>
                                <div className="absolute top-0 bottom-0 right-0 left-96 px-6 flex flex-col justify-center">
                                    <div className="relative h-8 w-full bg-zinc-900/50 rounded-lg overflow-hidden border border-zinc-800/50">
                                        <div className="absolute inset-0 flex items-center pointer-events-none">{game.tags.map(tag => (<div key={tag.id} className={`absolute h-4 w-0.5 rounded-full ${tag.category === 'Offense' ? 'bg-emerald-500' : (tag.category === 'Defense' ? 'bg-blue-500' : 'bg-zinc-600')} opacity-60`} style={{ left: `${(tag.startTime / (duration || 1)) * 100}%` }} />))}</div>
                                        <div className="absolute top-0 bottom-0 w-0.5 bg-white z-10 pointer-events-none" style={{ left: `${(currentTime / (duration || 1)) * 100}%` }}></div>
                                        <input type="range" min={0} max={duration || 100} step={0.1} value={currentTime} onChange={(e) => handleSeek(parseFloat(e.target.value))} className="w-full h-full opacity-0 cursor-pointer absolute inset-0 z-20" />
                                    </div>
                                    <div className="flex justify-between text-xs text-zinc-600 font-mono mt-1 px-1"><span>{formatTime(currentTime)}</span><span>{formatTime(duration)}</span></div>
                                </div>
                            </div>
                        </div>
                    )}

                    {view === 'comparison' && <ComparisonView game={game} mainVideoSrc={videoSrc} />}
                    {view === 'analytics' && <AnalyticsView game={game} onFilter={handleSetFilter} onSeek={handleSeek} />}
                    {view === 'matrix' && <DataMatrix tags={game.tags} categorizers={game.categorizers} descriptors={game.descriptors} players={game.players} homeTeamName={game.homeTeamName} awayTeamName={game.awayTeamName} onCellClick={handleSetFilter} />}
                    {view === 'playlists' && <PlaylistView game={game} playlists={playlists} activePlaylistId={activePlaylistId} onCreatePlaylist={(name) => { const newPl: Playlist = { id: generateId().toString(), name, items: [] }; setPlaylists([...playlists, newPl]); setActivePlaylistId(newPl.id); }} onDeletePlaylist={(id) => { setPlaylists(playlists.filter(p => p.id !== id)); if (activePlaylistId === id) setActivePlaylistId(null); }} onSelectPlaylist={setActivePlaylistId} onReorderItem={handleReorderPlaylistItem} onRemoveItem={handleRemovePlaylistItem} onPlayPlaylist={handlePlayPlaylist} />}
                </React.Suspense>
            </main >

            <KeyboardOverlay isOpen={isShortcutsOpen} onClose={() => setIsShortcutsOpen(false)} categorizers={game.categorizers} descriptors={game.descriptors} players={game.players} homeTeamColor={game.homeTeamColor} awayTeamColor={game.awayTeamColor} />
            <Modal isOpen={isStartersModalOpen} onClose={() => setIsStartersModalOpen(false)} title="Select Starters" size="md">
                <div className="space-y-6"><p className="text-sm text-zinc-400">Select 5 players for each team to start the game.</p><div className="grid grid-cols-2 gap-8">{['home', 'away'].map((team: any) => (<div key={team}><h4 className={`text-sm font-bold uppercase mb-2 ${team === 'home' ? 'text-brand-500' : 'text-cyan-500'}`}>{team === 'home' ? game.homeTeamName : game.awayTeamName}</h4><div className="space-y-1">{game.players.filter(p => p.team === team).map(p => (<button key={p.id} onClick={() => handleToggleLineup(p.id)} className={`w-full flex items-center justify-between p-2 rounded border text-sm transition-all ${game.activeLineup.includes(p.id) ? (team === 'home' ? 'bg-brand-900/20 border-brand-500 text-white' : 'bg-cyan-900/20 border-cyan-500 text-white') : 'bg-zinc-900 border-zinc-800 text-zinc-500 hover:bg-zinc-800'}`}><span>#{p.number} {p.name}</span>{game.activeLineup.includes(p.id) && <CheckCircle size={14} />}</button>))}</div></div>))}</div><div className="flex justify-end pt-4 border-t border-zinc-800"><button onClick={() => setIsStartersModalOpen(false)} className="bg-white text-black font-bold px-6 py-2 rounded text-sm hover:bg-zinc-200">Done</button></div></div>
            </Modal>
            <Modal isOpen={isExportModalOpen} onClose={() => setIsExportModalOpen(false)} title="Export Data" size="md">
                <div className="space-y-6"><div><label className="block text-xs font-bold text-zinc-500 uppercase mb-2">Filename</label><input ref={exportInputRef} className="w-full bg-zinc-950 border border-zinc-800 p-2 rounded text-white text-sm" value={exportFileName} onChange={e => setExportFileName(e.target.value)} /></div><div><label className="block text-xs font-bold text-zinc-500 uppercase mb-2">Format</label><div className="grid grid-cols-2 gap-2"><button onClick={() => setExportConfig({ ...exportConfig, type: 'analytics' })} className={`p-3 rounded border text-left ${exportConfig.type === 'analytics' ? 'bg-zinc-800 border-white text-white' : 'bg-zinc-900 border-zinc-800 text-zinc-400'}`}><div className="font-bold text-sm mb-1 flex items-center gap-2"><FileSpreadsheet size={14} /> Analytics Report</div><div className="text-[10px]">Comprehensive CSV / Excel compatible file with all advanced stats.</div></button><button onClick={() => setExportConfig({ ...exportConfig, type: 'raw' })} className={`p-3 rounded border text-left ${exportConfig.type === 'raw' ? 'bg-zinc-800 border-white text-white' : 'bg-zinc-900 border-zinc-800 text-zinc-400'}`}><div className="font-bold text-sm mb-1">Raw CSV</div><div className="text-[10px]">All events with timestamp, location, and details.</div></button><button onClick={() => setExportConfig({ ...exportConfig, type: 'box' })} className={`p-3 rounded border text-left ${exportConfig.type === 'box' ? 'bg-zinc-800 border-white text-white' : 'bg-zinc-900 border-zinc-800 text-zinc-400'}`}><div className="font-bold text-sm mb-1">Box Score CSV</div><div className="text-[10px]">Simple aggregated stats per player (PTS, REB, AST, etc).</div></button><button onClick={() => setExportConfig({ ...exportConfig, type: 'pbp' })} className={`p-3 rounded border text-left ${exportConfig.type === 'pbp' ? 'bg-zinc-800 border-white text-white' : 'bg-zinc-900 border-zinc-800 text-zinc-400'}`}><div className="font-bold text-sm mb-1">Play-by-Play CSV</div><div className="text-[10px]">Readable game log with running score.</div></button><button onClick={() => setExportConfig({ ...exportConfig, type: 'xml' })} className={`p-3 rounded border text-left ${exportConfig.type === 'xml' ? 'bg-zinc-800 border-white text-white' : 'bg-zinc-900 border-zinc-800 text-zinc-400'}`}><div className="font-bold text-sm mb-1">Premiere XML</div><div className="text-[10px]">Timeline sequence for video editing software.</div></button><button onClick={() => setExportConfig({ ...exportConfig, type: 'playlists' })} className={`p-3 rounded border text-left ${exportConfig.type === 'playlists' ? 'bg-zinc-800 border-white text-white' : 'bg-zinc-900 border-zinc-800 text-zinc-400'}`}><div className="font-bold text-sm mb-1">Playlists CSV</div><div className="text-[10px]">Export custom playlists and their clips to CSV.</div></button></div></div><div className="bg-zinc-900/50 p-4 rounded border border-white/5 flex items-center justify-between"><div><div className="font-bold text-sm text-white mb-1 flex items-center gap-2"><Film size={16} /> Burned Video (MP4)</div><div className="text-[10px] text-zinc-500">Export video with telestrations & overlays baked in.</div></div><button onClick={handleRenderVideo} disabled={!videoSrc} className="bg-orange-600 hover:bg-orange-500 disabled:opacity-50 disabled:cursor-not-allowed text-white px-4 py-2 rounded-lg text-xs font-bold transition-colors flex items-center gap-2">{videoSrc ? 'Render Video' : 'No Video Source'} <ChevronRight size={14} /></button></div>{exportConfig.type !== 'xml' && exportConfig.type !== 'raw' && exportConfig.type !== 'playlists' && exportConfig.type !== 'analytics' && (<div><label className="block text-xs font-bold text-zinc-500 uppercase mb-2">Scope</label><div className="flex bg-zinc-900 rounded p-1 border border-zinc-800"><button onClick={() => setExportConfig({ ...exportConfig, scope: 'game' })} className={`flex-1 py-1.5 text-xs font-bold rounded ${exportConfig.scope === 'game' ? 'bg-zinc-700 text-white' : 'text-zinc-500'}`}>Full Game</button><button onClick={() => setExportConfig({ ...exportConfig, scope: 'half' })} className={`flex-1 py-1.5 text-xs font-bold rounded ${exportConfig.scope === 'half' ? 'bg-zinc-700 text-white' : 'text-zinc-500'}`}>By Half</button><button onClick={() => setExportConfig({ ...exportConfig, scope: 'quarter' })} className={`flex-1 py-1.5 text-xs font-bold rounded ${exportConfig.scope === 'quarter' ? 'bg-zinc-700 text-white' : 'text-zinc-500'}`}>Quarter</button></div></div>)}<div className="flex justify-end pt-4 border-t border-zinc-800"><button onClick={handlePerformExport} className="bg-white text-black font-bold px-6 py-2 rounded text-sm hover:bg-zinc-200">Download</button></div></div>
            </Modal>
            <Modal isOpen={isLocationModalOpen} onClose={() => setIsLocationModalOpen(false)} title="Select Location" size="md">
                <div className="aspect-square bg-zinc-950 border border-zinc-800 rounded relative overflow-hidden shadow-inner">
                    <CourtMap readOnly={false} onMapClick={handleSetTagLocation} />
                </div>
            </Modal>
        </div >
    );
};

const App: React.FC = () => {
    return (
        <GameProvider>
            <AppContent />
        </GameProvider>
    );
};

export default App;
