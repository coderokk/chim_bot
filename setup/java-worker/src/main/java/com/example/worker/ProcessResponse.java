package com.example.worker;

public class ProcessResponse {
    private String taskId;
    private String mainFileUrl;
    private String licenseFileUrl;
    private String accountPhone;
    // геттеры/сеттеры
    public String getTaskId() { return taskId; }
    public void setTaskId(String taskId) { this.taskId = taskId; }
    public String getMainFileUrl() { return mainFileUrl; }
    public void setMainFileUrl(String mainFileUrl) { this.mainFileUrl = mainFileUrl; }
    public String getLicenseFileUrl() { return licenseFileUrl; }
    public void setLicenseFileUrl(String licenseFileUrl) { this.licenseFileUrl = licenseFileUrl; }
    public String getAccountPhone() { return accountPhone; }
    public void setAccountPhone(String accountPhone) { this.accountPhone = accountPhone; }
}
