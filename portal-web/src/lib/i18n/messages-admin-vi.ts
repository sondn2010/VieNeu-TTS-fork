/** Admin-area message catalog — owned by phase 14. `AdminMessages` is the
 * type source of truth; `messages-admin-en.ts` is typed against it and also
 * exports `getAdminMessages(language)`, the small helper every admin
 * component uses instead of the main `useI18n()` catalog (admin strings are
 * deliberately kept out of `Messages`/`I18nProvider`, which phase 14 does
 * not own). */
export interface AdminMessages {
  nav: {
    usersTitle: string;
    dictionariesTitle: string;
    voicesTitle: string;
    auditLogTitle: string;
  };
  guard: {
    forbiddenRole: string;
    lastSuperadmin: string;
    selfModification: string;
    emailTaken: string;
    genericError: string;
  };
  users: {
    title: string;
    subtitle: string;
    searchPlaceholder: string;
    roleFilterAll: string;
    statusFilterAll: string;
    statusActive: string;
    statusInactive: string;
    createButton: string;
    columnEmail: string;
    columnUsername: string;
    columnRole: string;
    columnStatus: string;
    columnBalance: string;
    columnExpiry: string;
    columnLastLogin: string;
    columnRecordings: string;
    neverLoggedIn: string;
    noExpiry: string;
    loadMoreButton: string;
  };
  createUserDialog: {
    title: string;
    emailLabel: string;
    usernameLabel: string;
    passwordLabel: string;
    roleLabel: string;
    submitButton: string;
  };
  userDetail: {
    backToList: string;
    profileTitle: string;
    emailLabel: string;
    usernameLabel: string;
    saveButton: string;
    enableButton: string;
    disableButton: string;
    resetPasswordButton: string;
    deleteButton: string;
    roleLabel: string;
    roleAdminOnlyHint: string;
    quotaTitle: string;
    tokenDeltaLabel: string;
    tokenReasonLabel: string;
    tokenAdjustButton: string;
    resultingBalance: string;
    planTitle: string;
    planTierLabel: string;
    planQuotaTotalLabel: string;
    planDailyLimitLabel: string;
    planExpiryLabel: string;
    planResetDailyLabel: string;
    planSaveButton: string;
    apiKeysTitle: string;
    apiKeysEmpty: string;
    apiKeysColumnName: string;
    apiKeysColumnPrefix: string;
    apiKeysColumnEnv: string;
    apiKeysColumnLastUsed: string;
    apiKeysColumnRevoked: string;
    revokeButton: string;
    recordingsTitle: string;
  };
  resetPasswordDialog: {
    title: string;
    newPasswordLabel: string;
    confirmPasswordLabel: string;
    submitButton: string;
    errorMismatch: string;
    errorTooShort: string;
    success: string;
  };
  deleteUserDialog: {
    title: string;
    body: string;
    confirmEmailLabel: string;
    submitButton: string;
    errorMismatch: string;
  };
  dictionaries: {
    title: string;
    subtitle: string;
    createButton: string;
    columnName: string;
    columnKind: string;
    columnEnabled: string;
    columnRuleCount: string;
    importButton: string;
    exportJsonButton: string;
    exportTxtButton: string;
    deleteButton: string;
    openButton: string;
  };
  createDictionaryDialog: {
    title: string;
    nameLabel: string;
    kindLabel: string;
    submitButton: string;
  };
  importDictionaryDialog: {
    title: string;
    formatLabel: string;
    modeLabel: string;
    modeMerge: string;
    modeReplace: string;
    fileLabel: string;
    submitButton: string;
    rejectedSummary: string;
    lineErrorsSummary: string;
  };
  dictionaryDetail: {
    backToList: string;
    addRuleButton: string;
    saveButton: string;
    etagConflict: string;
    columnSource: string;
    columnReplacement: string;
    columnMode: string;
    modePhonetic: string;
    modeEnglishFallback: string;
    columnWholeWord: string;
    columnCaseSensitive: string;
    columnEnabled: string;
    columnNote: string;
    removeRowButton: string;
    previewTitle: string;
    previewPlaceholder: string;
  };
  voices: {
    title: string;
    subtitle: string;
    columnName: string;
    columnGender: string;
    columnRegion: string;
    columnActive: string;
    editButton: string;
  };
  voiceEditDrawer: {
    title: string;
    nameLabel: string;
    genderLabel: string;
    regionLabel: string;
    tagsLabel: string;
    tagsHint: string;
    languageLabelLabel: string;
    sortOrderLabel: string;
    activeLabel: string;
    saveButton: string;
    closeButton: string;
    avatarTitle: string;
    uploadAvatarButton: string;
    removeAvatarButton: string;
    sampleTitle: string;
    uploadSampleButton: string;
    renderSampleButton: string;
    renderTextLabel: string;
    renderTextPlaceholder: string;
  };
  auditLog: {
    title: string;
    subtitle: string;
    actorFilterPlaceholder: string;
    actionFilterPlaceholder: string;
    targetTypeFilterPlaceholder: string;
    targetIdFilterPlaceholder: string;
    fromLabel: string;
    toLabel: string;
    columnTime: string;
    columnActor: string;
    columnAction: string;
    columnTarget: string;
    expandDetails: string;
    beforeLabel: string;
    afterLabel: string;
  };
}

export const adminVi: AdminMessages = {
  nav: {
    usersTitle: "Người dùng",
    dictionariesTitle: "Từ điển hệ thống",
    voicesTitle: "Giọng đọc",
    auditLogTitle: "Nhật ký quản trị",
  },
  guard: {
    forbiddenRole: "Bạn không có quyền quản trị đối với tài khoản này.",
    lastSuperadmin: "Không thể thực hiện vì đây là siêu quản trị viên đang hoạt động cuối cùng.",
    selfModification: "Không thể thực hiện hành động này trên tài khoản của chính bạn.",
    emailTaken: "Email này đã được sử dụng.",
    genericError: "Có lỗi xảy ra. Vui lòng thử lại.",
  },
  users: {
    title: "Người dùng",
    subtitle: "Quản lý tài khoản, hạn mức và quyền truy cập",
    searchPlaceholder: "Tìm theo email hoặc tên người dùng...",
    roleFilterAll: "Tất cả quyền",
    statusFilterAll: "Tất cả trạng thái",
    statusActive: "Đang hoạt động",
    statusInactive: "Đã khóa",
    createButton: "+ Tạo người dùng",
    columnEmail: "Email",
    columnUsername: "Tên người dùng",
    columnRole: "Quyền",
    columnStatus: "Trạng thái",
    columnBalance: "Số dư / Hạn mức",
    columnExpiry: "Hết hạn",
    columnLastLogin: "Đăng nhập gần nhất",
    columnRecordings: "Số bản ghi",
    neverLoggedIn: "Chưa đăng nhập",
    noExpiry: "Không giới hạn",
    loadMoreButton: "Tải thêm",
  },
  createUserDialog: {
    title: "Tạo người dùng",
    emailLabel: "Email",
    usernameLabel: "Tên người dùng",
    passwordLabel: "Mật khẩu",
    roleLabel: "Quyền",
    submitButton: "Tạo",
  },
  userDetail: {
    backToList: "← Quay lại danh sách",
    profileTitle: "Hồ sơ",
    emailLabel: "Email",
    usernameLabel: "Tên người dùng",
    saveButton: "Lưu",
    enableButton: "Kích hoạt",
    disableButton: "Khóa tài khoản",
    resetPasswordButton: "Đặt lại mật khẩu",
    deleteButton: "Xóa tài khoản",
    roleLabel: "Quyền",
    roleAdminOnlyHint: "Chỉ siêu quản trị viên mới đổi được quyền.",
    quotaTitle: "Hạn mức",
    tokenDeltaLabel: "Số token thay đổi (+/-)",
    tokenReasonLabel: "Lý do",
    tokenAdjustButton: "Điều chỉnh",
    resultingBalance: "Số dư sau điều chỉnh",
    planTitle: "Gói dịch vụ",
    planTierLabel: "Hạng gói",
    planQuotaTotalLabel: "Tổng hạn mức token",
    planDailyLimitLabel: "Hạn mức ký tự/ngày",
    planExpiryLabel: "Ngày hết hạn",
    planResetDailyLabel: "Đặt lại hạn mức ngày hôm nay",
    planSaveButton: "Lưu gói",
    apiKeysTitle: "Khóa API",
    apiKeysEmpty: "Chưa có khóa API nào.",
    apiKeysColumnName: "Tên",
    apiKeysColumnPrefix: "Tiền tố",
    apiKeysColumnEnv: "Môi trường",
    apiKeysColumnLastUsed: "Dùng gần nhất",
    apiKeysColumnRevoked: "Đã thu hồi",
    revokeButton: "Thu hồi",
    recordingsTitle: "Bản ghi âm thanh",
  },
  resetPasswordDialog: {
    title: "Đặt lại mật khẩu",
    newPasswordLabel: "Mật khẩu mới",
    confirmPasswordLabel: "Nhập lại mật khẩu mới",
    submitButton: "Đặt lại",
    errorMismatch: "Hai mật khẩu không khớp.",
    errorTooShort: "Mật khẩu phải có ít nhất 10 ký tự.",
    success: "Đã đặt lại mật khẩu.",
  },
  deleteUserDialog: {
    title: "Xóa tài khoản?",
    body: "Hành động này không thể hoàn tác. Nhập email của tài khoản để xác nhận.",
    confirmEmailLabel: "Nhập email để xác nhận",
    submitButton: "Xóa vĩnh viễn",
    errorMismatch: "Email xác nhận không khớp.",
  },
  dictionaries: {
    title: "Từ điển hệ thống",
    subtitle: "Quản lý các bộ quy tắc phát âm dùng chung",
    createButton: "+ Tạo bộ từ điển",
    columnName: "Tên",
    columnKind: "Loại",
    columnEnabled: "Đang bật",
    columnRuleCount: "Số quy tắc",
    importButton: "Nhập",
    exportJsonButton: "Xuất JSON",
    exportTxtButton: "Xuất TXT",
    deleteButton: "Xóa",
    openButton: "Mở",
  },
  createDictionaryDialog: {
    title: "Tạo bộ từ điển",
    nameLabel: "Tên",
    kindLabel: "Loại",
    submitButton: "Tạo",
  },
  importDictionaryDialog: {
    title: "Nhập từ điển",
    formatLabel: "Định dạng",
    modeLabel: "Chế độ",
    modeMerge: "Gộp vào bộ hiện có",
    modeReplace: "Thay thế toàn bộ",
    fileLabel: "Chọn tệp",
    submitButton: "Nhập",
    rejectedSummary: "bị từ chối do kiểm duyệt",
    lineErrorsSummary: "dòng lỗi định dạng",
  },
  dictionaryDetail: {
    backToList: "← Quay lại danh sách",
    addRuleButton: "+ Thêm quy tắc",
    saveButton: "Lưu toàn bộ",
    etagConflict: "Bộ từ điển đã thay đổi từ nơi khác. Vui lòng tải lại trang và thử lại.",
    columnSource: "Từ gốc",
    columnReplacement: "Cách đọc",
    columnMode: "Kiểu",
    modePhonetic: "Đọc theo cách ghi",
    modeEnglishFallback: "Đọc tiếng Anh (fallback)",
    columnWholeWord: "Nguyên từ",
    columnCaseSensitive: "Phân biệt hoa/thường",
    columnEnabled: "Bật",
    columnNote: "Ghi chú",
    removeRowButton: "Xóa dòng",
    previewTitle: "Xem thử (trên trình duyệt)",
    previewPlaceholder: "Nhập văn bản để xem thử cách áp dụng quy tắc...",
  },
  voices: {
    title: "Giọng đọc",
    subtitle: "Quản lý danh mục giọng đọc của hệ thống",
    columnName: "Tên",
    columnGender: "Giới tính",
    columnRegion: "Vùng miền",
    columnActive: "Đang hoạt động",
    editButton: "Sửa",
  },
  voiceEditDrawer: {
    title: "Sửa giọng đọc",
    nameLabel: "Tên",
    genderLabel: "Giới tính",
    regionLabel: "Vùng miền",
    tagsLabel: "Thẻ mô tả",
    tagsHint: "cách nhau bằng dấu phẩy",
    languageLabelLabel: "Nhãn ngôn ngữ",
    sortOrderLabel: "Thứ tự hiển thị",
    activeLabel: "Đang hoạt động",
    saveButton: "Lưu",
    closeButton: "Đóng",
    avatarTitle: "Ảnh đại diện",
    uploadAvatarButton: "Tải ảnh lên",
    removeAvatarButton: "Xóa ảnh",
    sampleTitle: "Mẫu giọng đọc",
    uploadSampleButton: "Tải tệp âm thanh",
    renderSampleButton: "Tạo mẫu bằng engine",
    renderTextLabel: "Văn bản mẫu (tùy chọn)",
    renderTextPlaceholder: "Để trống để dùng câu mẫu mặc định",
  },
  auditLog: {
    title: "Nhật ký quản trị",
    subtitle: "Lịch sử mọi thay đổi do quản trị viên thực hiện",
    actorFilterPlaceholder: "Lọc theo người thực hiện...",
    actionFilterPlaceholder: "Lọc theo hành động...",
    targetTypeFilterPlaceholder: "Loại đối tượng...",
    targetIdFilterPlaceholder: "ID đối tượng...",
    fromLabel: "Từ ngày",
    toLabel: "Đến ngày",
    columnTime: "Thời gian",
    columnActor: "Người thực hiện",
    columnAction: "Hành động",
    columnTarget: "Đối tượng",
    expandDetails: "Xem chi tiết",
    beforeLabel: "Trước",
    afterLabel: "Sau",
  },
};
