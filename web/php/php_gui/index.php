<?php
session_start();
require_once 'includes/config.php';
require_once 'includes/functions.php';

$page = isset($_GET['page']) ? $_GET['page'] : 'dashboard';
?>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title><?php echo getPageTitle($page); ?> - Trade Surveillance</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <link href="assets/css/style.css" rel="stylesheet">
</head>
<body>
    <div class="container-fluid">
        <div class="row">
            <!-- Sidebar -->
            <nav class="col-md-3 col-lg-2 d-md-block sidebar collapse">
                <div class="position-sticky pt-4">
                    <div class="text-center mb-5 px-3">
                        <div class="d-flex align-items-center justify-content-center mb-2">
                            <i class="fas fa-shield-halved text-white fs-4 me-2"></i>
                            <h5 class="text-white mb-0">TradeSurv</h5>
                        </div>
                        <small class="text-white-50">Market Abuse Detector</small>
                    </div>
                    <ul class="nav flex-column">
                        <li class="nav-item">
                            <a class="nav-link <?php echo ($page == 'dashboard') ? 'active' : ''; ?>" href="?page=dashboard">
                                <i class="fas fa-chart-line me-2"></i> Dashboard
                            </a>
                        </li>
                        <li class="nav-item">
                            <a class="nav-link <?php echo ($page == 'alerts') ? 'active' : ''; ?>" href="?page=alerts">
                                <i class="fas fa-triangle-exclamation me-2"></i> Alerts
                            </a>
                        </li>
                        <li class="nav-item">
                            <a class="nav-link <?php echo ($page == 'traders') ? 'active' : ''; ?>" href="?page=traders">
                                <i class="fas fa-users me-2"></i> Traders
                            </a>
                        </li>
                        <li class="nav-item">
                            <a class="nav-link <?php echo ($page == 'pipeline') ? 'active' : ''; ?>" href="?page=pipeline">
                                <i class="fas fa-diagram-project me-2"></i> Pipeline
                            </a>
                        </li>
                        <li class="nav-item">
                            <a class="nav-link <?php echo ($page == 'graph') ? 'active' : ''; ?>" href="?page=graph">
                                <i class="fas fa-share-nodes me-2"></i> Graph Analysis
                            </a>
                        </li>
                        <li class="nav-item">
                            <a class="nav-link <?php echo ($page == 'api') ? 'active' : ''; ?>" href="?page=api">
                                <i class="fas fa-code me-2"></i> API
                            </a>
                        </li>
                    </ul>
                    <hr class="text-white-50 mx-3 mt-4">
                    <div class="text-center px-3">
                        <small class="text-white-50 d-block">Distributed System</small>
                        <small class="text-white-50">Kafka • Neo4j • PySpark</small>
                    </div>
                </div>
            </nav>

            <!-- Main content -->
            <main class="col-md-9 ms-sm-auto col-lg-10 px-md-4">
                <div class="d-flex justify-content-between flex-wrap flex-md-nowrap align-items-center pt-4 pb-3 mb-4">
                    <div>
                        <h1 class="h2 mb-1"><?php echo getPageTitle($page); ?></h1>
                        <p class="text-muted mb-0">Real-time market abuse detection and surveillance</p>
                    </div>
                    <div class="btn-toolbar mb-2 mb-md-0">
                        <div class="btn-group me-2">
                            <button type="button" class="btn btn-sm btn-outline-secondary" onclick="location.reload()">
                                <i class="fas fa-rotate-right me-1"></i> Refresh
                            </button>
                        </div>
                        <span class="badge bg-success d-flex align-items-center px-3">
                            <i class="fas fa-circle me-1" style="font-size: 0.5rem;"></i> System Online
                        </span>
                    </div>
                </div>
                <?php include "pages/{$page}.php"; ?>
            </main>
        </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    <script src="https://code.jquery.com/jquery-3.7.0.min.js"></script>
    <script src="assets/js/app.js"></script>
</body>
</html>
