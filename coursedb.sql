-- phpMyAdmin SQL Dump
-- version 5.2.1
-- https://www.phpmyadmin.net/
--
-- Host: 127.0.0.1
-- Generation Time: Jul 07, 2026 at 09:59 AM
-- Server version: 10.4.32-MariaDB
-- PHP Version: 8.2.12

SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
START TRANSACTION;
SET time_zone = "+00:00";


/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;

--
-- Database: `coursedb`
--

-- --------------------------------------------------------

--
-- Table structure for table `admins`
--

CREATE TABLE `admins` (
  `admin_id` int(11) NOT NULL,
  `username` varchar(100) NOT NULL,
  `password` varchar(255) NOT NULL,
  `full_name` varchar(150) NOT NULL,
  `role` enum('superadmin','staff') DEFAULT 'staff',
  `created_at` timestamp NOT NULL DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Table structure for table `courses`
--

CREATE TABLE `courses` (
  `course_id` int(11) NOT NULL,
  `course_code` varchar(20) NOT NULL,
  `course_title` varchar(150) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `courses`
--

INSERT INTO `courses` (`course_id`, `course_code`, `course_title`) VALUES
(1, 'it', 'Bachelor of Science in Information Technology (BSIT)'),
(2, 'marketing', 'Bachelor of Science in Marketing Management (BSMM)'),
(3, 'tourism', 'Bachelor of Science in Tourism Management (BSTM)'),
(4, 'beed', 'Bachelor of Elementary Education (BEED)'),
(5, 'bsed', 'Bachelor of Secondary Education (BSED)'),
(6, 'crim', 'Bachelor of Science in Criminology (BSCRIM)');

-- --------------------------------------------------------

--
-- Table structure for table `course_pathways`
--

CREATE TABLE `course_pathways` (
  `pathway_id` int(11) NOT NULL,
  `course_id` int(11) NOT NULL,
  `pathway_name` varchar(100) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Stand-in structure for view `leaderboard`
-- (See below for the actual view)
--
CREATE TABLE `leaderboard` (
`studentID` int(11)
,`first_name` varchar(100)
,`last_name` varchar(100)
,`section` varchar(100)
,`strand_name` varchar(50)
,`total_score` float
,`time_taken_seconds` int(11)
,`rank` bigint(21)
);

-- --------------------------------------------------------

--
-- Table structure for table `quiz_answers`
--

CREATE TABLE `quiz_answers` (
  `id` int(11) NOT NULL,
  `quiz_result_id` int(11) NOT NULL,
  `question_id` int(11) NOT NULL,
  `answer_value` tinyint(4) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Table structure for table `quiz_questions`
--

CREATE TABLE `quiz_questions` (
  `question_id` int(11) NOT NULL,
  `question_text` varchar(255) NOT NULL,
  `course_id` int(11) NOT NULL,
  `is_active` tinyint(1) DEFAULT 1
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Table structure for table `quiz_results`
--

CREATE TABLE `quiz_results` (
  `id` int(11) NOT NULL,
  `studentID` int(11) NOT NULL,
  `total_score` float NOT NULL DEFAULT 0,
  `time_taken_seconds` int(11) NOT NULL DEFAULT 0,
  `recommended_course_id` int(11) DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `alignment_score` varchar(10) DEFAULT NULL,
  `recommended_course` varchar(150) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `quiz_results`
--

INSERT INTO `quiz_results` (`id`, `studentID`, `total_score`, `time_taken_seconds`, `recommended_course_id`, `created_at`, `alignment_score`, `recommended_course`) VALUES
(1, 2, 71.2, 123, NULL, '2026-07-06 09:23:24', '97%', 'Bachelor of Science in Information Technology (BSIT)'),
(2, 3, 71.2, 111, NULL, '2026-07-06 09:39:04', '97%', 'Bachelor of Science in Information Technology (BSIT)');

-- --------------------------------------------------------

--
-- Table structure for table `recommendations`
--

CREATE TABLE `recommendations` (
  `id` int(11) NOT NULL,
  `studentID` int(11) NOT NULL,
  `recommended_course_id` int(11) NOT NULL,
  `alternative_course_id` int(11) DEFAULT NULL,
  `alignment_score` decimal(5,2) NOT NULL,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `recommendations`
--

INSERT INTO `recommendations` (`id`, `studentID`, `recommended_course_id`, `alternative_course_id`, `alignment_score`, `created_at`) VALUES
(1, 2, 1, 5, 97.00, '2026-07-06 09:23:24'),
(2, 3, 1, 5, 97.00, '2026-07-06 09:39:04');

-- --------------------------------------------------------

--
-- Table structure for table `strands`
--

CREATE TABLE `strands` (
  `strand_id` int(11) NOT NULL,
  `strand_name` varchar(50) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `strands`
--

INSERT INTO `strands` (`strand_id`, `strand_name`) VALUES
(2, 'ABM'),
(4, 'GAS'),
(3, 'HUMSS'),
(1, 'STEM'),
(6, 'TVL-HE'),
(5, 'TVL-ICT');

-- --------------------------------------------------------

--
-- Table structure for table `users`
--

CREATE TABLE `users` (
  `studentID` int(11) NOT NULL,
  `first_name` varchar(100) NOT NULL,
  `last_name` varchar(100) NOT NULL,
  `email` varchar(150) NOT NULL,
  `password` varchar(255) NOT NULL,
  `strand_id` int(11) DEFAULT NULL,
  `section` varchar(100) DEFAULT NULL,
  `created_at` timestamp NOT NULL DEFAULT current_timestamp(),
  `profile_picture` varchar(255) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Dumping data for table `users`
--

INSERT INTO `users` (`studentID`, `first_name`, `last_name`, `email`, `password`, `strand_id`, `section`, `created_at`, `profile_picture`) VALUES
(2, 'Test', 'User', 'test1783357000@example.com', 'pass123', 2, 'A', '2026-07-06 08:56:40', NULL),
(3, 'Justine James', 'Gepulla', 'gepulla.20231513@cscqc.edu.ph', 'gepulla20', 1, NULL, '2026-07-06 08:59:08', 'student_3_20260706173054.jpg');

-- --------------------------------------------------------

--
-- Structure for view `leaderboard`
--
DROP TABLE IF EXISTS `leaderboard`;

CREATE ALGORITHM=UNDEFINED DEFINER=`root`@`localhost` SQL SECURITY DEFINER VIEW `leaderboard`  AS SELECT `u`.`studentID` AS `studentID`, `u`.`first_name` AS `first_name`, `u`.`last_name` AS `last_name`, `u`.`section` AS `section`, `s`.`strand_name` AS `strand_name`, `best`.`total_score` AS `total_score`, `best`.`time_taken_seconds` AS `time_taken_seconds`, rank() over ( order by `best`.`total_score` desc,`best`.`time_taken_seconds`) AS `rank` FROM (((select `quiz_results`.`studentID` AS `studentID`,max(`quiz_results`.`total_score`) AS `total_score`,min(`quiz_results`.`time_taken_seconds`) AS `time_taken_seconds` from `quiz_results` group by `quiz_results`.`studentID`) `best` join `users` `u` on(`u`.`studentID` = `best`.`studentID`)) left join `strands` `s` on(`s`.`strand_id` = `u`.`strand_id`)) ;

--
-- Indexes for dumped tables
--

--
-- Indexes for table `admins`
--
ALTER TABLE `admins`
  ADD PRIMARY KEY (`admin_id`),
  ADD UNIQUE KEY `username` (`username`);

--
-- Indexes for table `courses`
--
ALTER TABLE `courses`
  ADD PRIMARY KEY (`course_id`),
  ADD UNIQUE KEY `course_code` (`course_code`);

--
-- Indexes for table `course_pathways`
--
ALTER TABLE `course_pathways`
  ADD PRIMARY KEY (`pathway_id`),
  ADD KEY `idx_pathway_course` (`course_id`);

--
-- Indexes for table `quiz_answers`
--
ALTER TABLE `quiz_answers`
  ADD PRIMARY KEY (`id`),
  ADD KEY `question_id` (`question_id`),
  ADD KEY `idx_answer_result` (`quiz_result_id`);

--
-- Indexes for table `quiz_questions`
--
ALTER TABLE `quiz_questions`
  ADD PRIMARY KEY (`question_id`),
  ADD KEY `idx_question_course` (`course_id`);

--
-- Indexes for table `quiz_results`
--
ALTER TABLE `quiz_results`
  ADD PRIMARY KEY (`id`),
  ADD KEY `recommended_course_id` (`recommended_course_id`),
  ADD KEY `idx_quiz_student` (`studentID`),
  ADD KEY `idx_quiz_score` (`total_score`);

--
-- Indexes for table `recommendations`
--
ALTER TABLE `recommendations`
  ADD PRIMARY KEY (`id`),
  ADD KEY `recommended_course_id` (`recommended_course_id`),
  ADD KEY `alternative_course_id` (`alternative_course_id`),
  ADD KEY `idx_rec_student` (`studentID`);

--
-- Indexes for table `strands`
--
ALTER TABLE `strands`
  ADD PRIMARY KEY (`strand_id`),
  ADD UNIQUE KEY `strand_name` (`strand_name`);

--
-- Indexes for table `users`
--
ALTER TABLE `users`
  ADD PRIMARY KEY (`studentID`),
  ADD UNIQUE KEY `email` (`email`),
  ADD KEY `idx_users_strand` (`strand_id`);

--
-- AUTO_INCREMENT for dumped tables
--

--
-- AUTO_INCREMENT for table `admins`
--
ALTER TABLE `admins`
  MODIFY `admin_id` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT for table `courses`
--
ALTER TABLE `courses`
  MODIFY `course_id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=7;

--
-- AUTO_INCREMENT for table `course_pathways`
--
ALTER TABLE `course_pathways`
  MODIFY `pathway_id` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT for table `quiz_answers`
--
ALTER TABLE `quiz_answers`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT for table `quiz_questions`
--
ALTER TABLE `quiz_questions`
  MODIFY `question_id` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT for table `quiz_results`
--
ALTER TABLE `quiz_results`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=3;

--
-- AUTO_INCREMENT for table `recommendations`
--
ALTER TABLE `recommendations`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=3;

--
-- AUTO_INCREMENT for table `strands`
--
ALTER TABLE `strands`
  MODIFY `strand_id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=7;

--
-- AUTO_INCREMENT for table `users`
--
ALTER TABLE `users`
  MODIFY `studentID` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=4;

--
-- Constraints for dumped tables
--

--
-- Constraints for table `course_pathways`
--
ALTER TABLE `course_pathways`
  ADD CONSTRAINT `course_pathways_ibfk_1` FOREIGN KEY (`course_id`) REFERENCES `courses` (`course_id`) ON DELETE CASCADE;

--
-- Constraints for table `quiz_answers`
--
ALTER TABLE `quiz_answers`
  ADD CONSTRAINT `quiz_answers_ibfk_1` FOREIGN KEY (`quiz_result_id`) REFERENCES `quiz_results` (`id`) ON DELETE CASCADE,
  ADD CONSTRAINT `quiz_answers_ibfk_2` FOREIGN KEY (`question_id`) REFERENCES `quiz_questions` (`question_id`);

--
-- Constraints for table `quiz_questions`
--
ALTER TABLE `quiz_questions`
  ADD CONSTRAINT `quiz_questions_ibfk_1` FOREIGN KEY (`course_id`) REFERENCES `courses` (`course_id`);

--
-- Constraints for table `quiz_results`
--
ALTER TABLE `quiz_results`
  ADD CONSTRAINT `quiz_results_ibfk_1` FOREIGN KEY (`studentID`) REFERENCES `users` (`studentID`) ON DELETE CASCADE,
  ADD CONSTRAINT `quiz_results_ibfk_2` FOREIGN KEY (`recommended_course_id`) REFERENCES `courses` (`course_id`);

--
-- Constraints for table `recommendations`
--
ALTER TABLE `recommendations`
  ADD CONSTRAINT `recommendations_ibfk_1` FOREIGN KEY (`studentID`) REFERENCES `users` (`studentID`) ON DELETE CASCADE,
  ADD CONSTRAINT `recommendations_ibfk_2` FOREIGN KEY (`recommended_course_id`) REFERENCES `courses` (`course_id`),
  ADD CONSTRAINT `recommendations_ibfk_3` FOREIGN KEY (`alternative_course_id`) REFERENCES `courses` (`course_id`);

--
-- Constraints for table `users`
--
ALTER TABLE `users`
  ADD CONSTRAINT `users_ibfk_1` FOREIGN KEY (`strand_id`) REFERENCES `strands` (`strand_id`);
COMMIT;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
