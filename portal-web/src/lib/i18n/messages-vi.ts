/** The Vietnamese catalog is the type source of truth; `messages-en.ts` is
 * typed against `Messages` so the two can never drift in shape. */
export interface Messages {
  common: {
    appName: string;
    loading: string;
    cancel: string;
    save: string;
    close: string;
    comingSoon: string;
  };
  auth: {
    loginTitle: string;
    signupTitle: string;
    emailLabel: string;
    passwordLabel: string;
    loginButton: string;
    signupButton: string;
    goToSignup: string;
    goToLogin: string;
    invalidCredentials: string;
    signupDisabled: string;
    signupRateLimited: string;
    emailTaken: string;
    passwordTooShort: string;
    genericError: string;
  };
  sidebar: {
    groupCreate: string;
    groupLibrary: string;
    groupAccount: string;
    groupAdmin: string;
    studio: string;
    podcast: string;
    stories: string;
    dubbing: string;
    lectures: string;
    voices: string;
    leaderboard: string;
    voiceCloning: string;
    community: string;
    downloadApp: string;
    dashboard: string;
    billing: string;
    developer: string;
    dictionary: string;
    adminUsers: string;
    adminDictionaries: string;
    adminVoices: string;
    adminAuditLog: string;
    tokenBalance: string;
    help: string;
    logout: string;
  };
  profile: {
    changePassword: string;
    planLabel: string;
  };
  changePasswordDialog: {
    title: string;
    currentPasswordLabel: string;
    newPasswordLabel: string;
    confirmPasswordLabel: string;
    submitButton: string;
    errorMismatch: string;
    errorTooShort: string;
    errorWrongCurrent: string;
    success: string;
  };
  terms: {
    title: string;
    subtitle: string;
    intro: string;
    allowedTitle: string;
    allowedText: string;
    prohibitedTitle: string;
    prohibitedItems: readonly string[];
    checkboxLabel: string;
    acceptButton: string;
    genericError: string;
  };
  studio: {
    voiceSelectorLabel: string;
    emotionLabel: string;
    emotionCry: string;
    emotionSigh: string;
    emotionClearThroat: string;
    bgMusicLabel: string;
    uploadFileButton: string;
    dictionaryLink: string;
    helpTooltip: string;
    onboardingStart: string;
    onboardingDonePrefix: string;
    onboardingHide: string;
    bannerText: string;
    editorPlaceholder: string;
    insertSampleButton: string;
    dragDropHint: string;
    counterCharsSuffix: string;
    counterTokensPrefix: string;
    counterTokensSuffix: string;
    counterRemainingPrefix: string;
    playNowButton: string;
    stopButton: string;
    generateButton: string;
    recentRecordingsTitle: string;
    refreshButton: string;
    downloadButton: string;
    deleteButton: string;
    retryHint: string;
    errorContentPolicy: string;
    errorTextTooLong: string;
    errorSynthesisInProgress: string;
    errorQuota: string;
    errorTermsNotAccepted: string;
    errorServiceUnavailable: string;
    errorGeneric: string;
  };
  library: {
    title: string;
    subtitle: string;
    searchPlaceholder: string;
    voiceFilterAll: string;
    createNewButton: string;
    countInfix: string;
    countSuffix: string;
    totalDurationLabel: string;
    loadMoreButton: string;
    emptyTitle: string;
    emptySubtitle: string;
    errorLoading: string;
    deleteConfirmTitle: string;
    deleteConfirmBody: string;
    deleteConfirmButton: string;
    deleteButtonLabel: string;
  };
}

export const vi: Messages = {
  common: {
    appName: "VieNeu",
    loading: "Đang tải...",
    cancel: "Hủy",
    save: "Lưu",
    close: "Đóng",
    comingSoon: "Sắp có",
  },
  auth: {
    loginTitle: "Đăng nhập",
    signupTitle: "Đăng ký",
    emailLabel: "Email",
    passwordLabel: "Mật khẩu",
    loginButton: "Đăng nhập",
    signupButton: "Đăng ký",
    goToSignup: "Chưa có tài khoản? Đăng ký",
    goToLogin: "Đã có tài khoản? Đăng nhập",
    invalidCredentials: "Email hoặc mật khẩu không đúng.",
    signupDisabled: "Đăng ký hiện đang tạm đóng.",
    signupRateLimited: "Quá nhiều yêu cầu đăng ký. Vui lòng thử lại sau.",
    emailTaken: "Email này đã được sử dụng.",
    passwordTooShort: "Mật khẩu phải có ít nhất 10 ký tự.",
    genericError: "Có lỗi xảy ra. Vui lòng thử lại.",
  },
  sidebar: {
    groupCreate: "TẠO",
    groupLibrary: "THƯ VIỆN",
    groupAccount: "TÀI KHOẢN",
    groupAdmin: "QUẢN TRỊ",
    studio: "Phòng thu",
    podcast: "Podcast",
    stories: "Truyện",
    dubbing: "Lồng tiếng",
    lectures: "Bài giảng",
    voices: "Giọng nói",
    leaderboard: "Bảng xếp hạng",
    voiceCloning: "Nhân bản giọng",
    community: "Cộng đồng",
    downloadApp: "Tải ứng dụng",
    dashboard: "Bảng điều khiển",
    billing: "Thanh toán",
    developer: "Nhà phát triển",
    dictionary: "Từ điển phát âm",
    adminUsers: "Người dùng",
    adminDictionaries: "Từ điển hệ thống",
    adminVoices: "Giọng đọc",
    adminAuditLog: "Nhật ký quản trị",
    tokenBalance: "Số dư token",
    help: "Trợ giúp & liên hệ",
    logout: "Đăng xuất",
  },
  profile: {
    changePassword: "Đổi mật khẩu",
    planLabel: "Gói",
  },
  changePasswordDialog: {
    title: "Đổi mật khẩu",
    currentPasswordLabel: "Mật khẩu hiện tại",
    newPasswordLabel: "Mật khẩu mới",
    confirmPasswordLabel: "Nhập lại mật khẩu mới",
    submitButton: "Đổi mật khẩu",
    errorMismatch: "Hai mật khẩu mới không khớp.",
    errorTooShort: "Mật khẩu mới phải có ít nhất 10 ký tự.",
    errorWrongCurrent: "Mật khẩu hiện tại không đúng.",
    success: "Đã đổi mật khẩu thành công.",
  },
  terms: {
    title: "Điều khoản tạo giọng nói",
    subtitle: "Vui lòng đọc kỹ trước khi sử dụng",
    intro:
      "Trước khi tạo giọng nói, vui lòng đọc và đồng ý với các điều khoản sau. Mọi văn bản đều được hệ thống AI kiểm duyệt trước khi tạo.",
    allowedTitle: "Được phép",
    allowedText: "Nội dung hợp pháp, lịch sử cho mục đích cá nhân, giáo dục, kinh doanh, sáng tạo và giải trí.",
    prohibitedTitle: "Không được phép",
    prohibitedItems: [
      "Ngôn từ tục tĩu mang tính lăng mạ, xúc phạm nghiêm trọng (ngôn ngữ đời thường vẫn được chấp nhận).",
      "Nội dung khiêu dâm hoặc gợi dục.",
      "Lăng mạ, bôi nhọ, phân biệt, kích động thù ghét hoặc quấy rối.",
      "Nội dung xuyên tạc, chống phá Nhà nước, Đảng, lãnh đạo hoặc chủ quyền quốc gia Việt Nam.",
      "Kêu gọi bạo lực, tự gây hại hoặc hành vi vi phạm pháp luật.",
    ],
    checkboxLabel: "Tôi đã đọc và đồng ý với các điều khoản trên.",
    acceptButton: "Đồng ý và tiếp tục",
    genericError: "Không thể lưu. Vui lòng thử lại.",
  },
  studio: {
    voiceSelectorLabel: "GIỌNG NÓI",
    emotionLabel: "Cảm xúc:",
    emotionCry: "Cười",
    emotionSigh: "Thở dài",
    emotionClearThroat: "Hắng giọng",
    bgMusicLabel: "Nhạc nền",
    uploadFileButton: "Tải tệp",
    dictionaryLink: "Từ điển",
    helpTooltip: "Hướng dẫn sử dụng Phòng thu",
    onboardingStart: "Bắt đầu",
    onboardingDonePrefix: "Đã xong",
    onboardingHide: "Ẩn",
    bannerText:
      "Mới: VieNeu giờ đọc được cả công thức toán học và hoá học! Cứ gõ tự nhiên như ax² + bx + c = 0, Δ ≥ 0, x ∈ ℝ hay 2H2 + O2 → 2H2O — hệ thống tự nhận diện và đọc đúng.",
    editorPlaceholder: "Nhập hoặc dán văn bản của bạn vào đây...",
    insertSampleButton: "✨ Chèn câu mẫu",
    dragDropHint: "hoặc kéo thả tệp .txt vào đây",
    counterCharsSuffix: "ký tự",
    counterTokensPrefix: "~",
    counterTokensSuffix: "token",
    counterRemainingPrefix: "còn",
    playNowButton: "Phát ngay",
    stopButton: "Dừng",
    generateButton: "Tạo giọng nói",
    recentRecordingsTitle: "CÁC BẢN GHI GẦN ĐÂY",
    refreshButton: "Làm mới",
    downloadButton: "Tải xuống",
    deleteButton: "Xóa",
    retryHint: "Đã gián đoạn, thử lại",
    errorContentPolicy: "Nội dung vi phạm điều khoản sử dụng.",
    errorTextTooLong:
      "Văn bản sau xử lý quá dài (do công thức hoặc từ điển mở rộng). Hãy rút ngắn văn bản.",
    errorSynthesisInProgress: "Mỗi lần chỉ tạo được một giọng nói. Vui lòng chờ.",
    errorQuota: "Bạn đã hết hạn mức token hoặc ký tự hôm nay.",
    errorTermsNotAccepted: "Vui lòng đồng ý lại điều khoản sử dụng.",
    errorServiceUnavailable: "Hệ thống đang bận. Vui lòng thử lại sau.",
    errorGeneric: "Có lỗi xảy ra. Vui lòng thử lại.",
  },
  library: {
    title: "Giọng nói của tôi",
    subtitle: "Xem và quản lý giọng nói đã tạo",
    searchPlaceholder: "Tìm kiếm theo văn bản hoặc giọng...",
    voiceFilterAll: "Tất cả giọng",
    createNewButton: "+ Tạo mới",
    countInfix: "trong số",
    countSuffix: "giọng nói",
    totalDurationLabel: "Tổng thời lượng:",
    loadMoreButton: "Tải thêm",
    emptyTitle: "Chưa có bản ghi nào",
    emptySubtitle: "Tạo giọng nói đầu tiên của bạn ở Phòng thu",
    errorLoading: "Không thể tải danh sách. Vui lòng thử lại.",
    deleteConfirmTitle: "Xóa bản ghi?",
    deleteConfirmBody: "Bản ghi sẽ bị xóa vĩnh viễn và không thể hoàn tác.",
    deleteConfirmButton: "Xóa",
    deleteButtonLabel: "Xóa bản ghi",
  },
};
